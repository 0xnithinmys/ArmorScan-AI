from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.models import Scan, Target, User


SAFE_ACTIONS = {
    "http.get",
    "http.head",
    "browser.navigate",
    "browser.extract_accessibility_tree",
    "browser.capture_network",
    "browser.capture_screenshot",
    "scanner.nuclei",
    "scanner.zap",
    "scanner.semgrep",
    "scanner.bandit",
    "scanner.gitleaks",
    "scanner.trivy",
}
BLOCKED_PAYLOAD_MARKERS = [
    "rm -rf",
    "powershell",
    "cmd.exe",
    "/etc/passwd",
    "aws_secret",
    "metadata.google.internal",
    "169.254.169.254",
]


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    action: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "action": self.action,
            "details": self.details,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


class PolicyViolation(Exception):
    def __init__(self, decision: PolicyDecision) -> None:
        super().__init__(decision.reason)
        self.decision = decision


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode_b64url(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _canonical_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _host_from_value(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return parsed.hostname


def _normalize_scope_hosts(target: Target) -> list[str]:
    hosts = {_host_from_value(target.target_url)}
    for item in target.scope or []:
        hosts.add(_host_from_value(item))
    return sorted(host for host in hosts if host)


def _url_allowed(url: str, allowed_hosts: list[str]) -> bool:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in settings.POLICY_ALLOWED_SCHEMES:
        return False
    host = parsed.hostname
    if not host:
        return False
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


def build_intent_plan(*, scan: Scan, target: Target, user: User) -> dict[str, Any]:
    allowed_hosts = _normalize_scope_hosts(target)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.ARMORIQ_INTENT_TTL_SECONDS)
    return {
        "version": "armorscan.intent.v1",
        "scan_id": scan.id,
        "target_id": target.id,
        "requested_by_id": user.id,
        "target_url": target.target_url,
        "scan_type": scan.scan_type,
        "allowed_hosts": allowed_hosts,
        "allowed_actions": sorted(SAFE_ACTIONS),
        "limits": {
            "max_requests": settings.POLICY_MAX_REQUESTS_PER_SCAN,
            "allowed_schemes": settings.POLICY_ALLOWED_SCHEMES,
            "active_destructive_tests": False,
        },
        "expires_at": expires_at.isoformat(),
    }


def sign_intent_plan(intent_plan: dict[str, Any]) -> str:
    payload = _b64url(_canonical_json(intent_plan))
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload.encode("ascii"), hashlib.sha256)
    return f"{payload}.{_b64url(signature.digest())}"


def verify_intent_token(token: str) -> dict[str, Any] | None:
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload.encode("ascii"), hashlib.sha256)
        if not hmac.compare_digest(_b64url(expected.digest()), signature):
            return None
        intent_plan = json.loads(_decode_b64url(payload))
        expires_at = datetime.fromisoformat(str(intent_plan["expires_at"]).replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None
        return intent_plan
    except Exception:
        return None


def evaluate_scan_request(*, scan: Scan, target: Target, user: User) -> PolicyDecision:
    if target.owner_id != user.id:
        return PolicyDecision(False, "Target does not belong to requester", "scan.create", {})
    if target.authorization_status != "verified":
        return PolicyDecision(False, "Target authorization is not verified", "scan.create", {})
    if scan.scan_type not in {"url", "api", "github"}:
        return PolicyDecision(False, "Unsupported scan type", "scan.create", {"scan_type": scan.scan_type})
    if scan.scan_type in {"url", "api"} and not _url_allowed(target.target_url, _normalize_scope_hosts(target)):
        return PolicyDecision(False, "Target URL is outside approved scope", "scan.create", {})
    return PolicyDecision(True, "Scan request satisfies local ArmorIQ policy", "scan.create", {})


def evaluate_tool_action(
    *,
    token: str | None,
    action: str,
    url: str | None = None,
    payload: str | None = None,
) -> PolicyDecision:
    if not token:
        return PolicyDecision(False, "Missing ArmorIQ intent token", action, {})
    intent_plan = verify_intent_token(token)
    if intent_plan is None:
        return PolicyDecision(False, "Invalid or expired ArmorIQ intent token", action, {})
    if action not in intent_plan["allowed_actions"]:
        return PolicyDecision(False, "Action is not present in signed intent plan", action, {})
    if url and not _url_allowed(url, intent_plan["allowed_hosts"]):
        return PolicyDecision(False, "URL is outside signed intent scope", action, {"url": url})
    if payload and any(marker in payload.lower() for marker in BLOCKED_PAYLOAD_MARKERS):
        return PolicyDecision(False, "Payload violates destructive/exfiltration policy", action, {})
    return PolicyDecision(True, "Action allowed by signed intent plan", action, {"url": url})


def require_allowed(decision: PolicyDecision) -> None:
    if not decision.allowed and settings.ARMORIQ_FAIL_CLOSED:
        raise PolicyViolation(decision)
