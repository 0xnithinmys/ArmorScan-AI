from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


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
class AgentPolicyDecision:
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


def _url_allowed(url: str, allowed_hosts: list[str], allowed_schemes: list[str]) -> bool:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in allowed_schemes:
        return False
    host = parsed.hostname
    if not host:
        return False
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


def evaluate_agent_action(
    *,
    intent_plan: dict[str, Any] | None,
    token: str | None,
    action: str,
    url: str | None = None,
    payload: str | None = None,
) -> AgentPolicyDecision:
    if not token:
        return AgentPolicyDecision(False, "Missing ArmorIQ intent token", action, {})
    if not intent_plan:
        return AgentPolicyDecision(False, "Missing signed intent plan", action, {})
    if action not in intent_plan.get("allowed_actions", []):
        return AgentPolicyDecision(False, "Action is outside signed plan", action, {})
    if url and not _url_allowed(
        url,
        intent_plan.get("allowed_hosts", []),
        intent_plan.get("limits", {}).get("allowed_schemes", ["http", "https"]),
    ):
        return AgentPolicyDecision(False, "URL is outside signed scope", action, {"url": url})
    if payload and any(marker in payload.lower() for marker in BLOCKED_PAYLOAD_MARKERS):
        return AgentPolicyDecision(False, "Payload violates safety policy", action, {})
    return AgentPolicyDecision(True, "Action allowed by signed intent plan", action, {"url": url})
