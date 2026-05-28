from __future__ import annotations

import asyncio
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.models import Target, TargetAuthorizationProof, User

try:
    import dns.asyncresolver
except ImportError:  # pragma: no cover - optional dependency in local dev before install
    dns = None
else:  # pragma: no cover - imported dynamically in runtime environments
    dns = dns.asyncresolver


SUPPORTED_PROOF_TYPES = {
    "manual_attestation",
    "dns_txt",
    "http_file",
    "meta_tag",
    "github_file",
}
VERIFIED_PROOF_TYPES = {"dns_txt", "http_file", "meta_tag", "github_file"}


@dataclass(slots=True)
class VerificationResult:
    ok: bool
    status: str
    message: str
    submitted_value: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_target_url(value: str) -> tuple[str | None, str]:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.hostname
    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else value.rstrip("/")
    return host, base_url.rstrip("/")


def _repo_slug(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.netloc.lower() != "github.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return f"{owner}/{repo}"


def _expiry() -> datetime:
    return _now() + timedelta(hours=settings.TARGET_AUTH_PROOF_TTL_HOURS)


def create_proof_challenge(*, target: Target, user: User, proof_type: str) -> TargetAuthorizationProof:
    if proof_type not in SUPPORTED_PROOF_TYPES:
        raise ValueError(f"Unsupported proof type: {proof_type}")

    token = secrets.token_urlsafe(24)
    expected_value = f"armorscan-site-verification={token}"
    host, base_url = _parse_target_url(target.target_url)
    metadata: dict[str, str] = {}

    if proof_type == "dns_txt":
        verification_target = host or target.target_url
        instructions = (
            f"Create a DNS TXT record for {verification_target} with the exact value "
            f"'{expected_value}', then verify before the challenge expires."
        )
    elif proof_type == "http_file":
        verification_target = f"{base_url}/.well-known/armorscan-verification.txt"
        instructions = (
            "Publish a plain-text file at /.well-known/armorscan-verification.txt containing "
            f"the exact value '{expected_value}'."
        )
    elif proof_type == "meta_tag":
        verification_target = target.target_url
        instructions = (
            'Add <meta name="armorscan-verification" '
            f'content="{token}"> to the HTML of the target page, then verify it.'
        )
    elif proof_type == "github_file":
        slug = _repo_slug(target.target_url)
        if not slug:
            raise ValueError("GitHub file proof requires a github.com repository URL target")
        verification_target = f"{slug}:armorscan-verification.txt"
        metadata["repo_slug"] = slug
        instructions = (
            "Create a repository-root file named armorscan-verification.txt containing the exact "
            f"value '{expected_value}'. Provide the raw GitHub file URL when verifying."
        )
    else:
        verification_target = "manual"
        instructions = (
            "Manual attestation does not fully verify ownership. It only records an attested status."
        )

    return TargetAuthorizationProof(
        target_id=target.id,
        created_by_id=user.id,
        proof_type=proof_type,
        status="pending" if proof_type != "manual_attestation" else "attested",
        challenge_token=token,
        verification_target=verification_target,
        expected_value=expected_value,
        instructions=instructions,
        metadata_json=metadata,
        expires_at=_expiry() if proof_type != "manual_attestation" else None,
    )


async def verify_proof(*, target: Target, proof: TargetAuthorizationProof, submitted_value: str | None) -> VerificationResult:
    if proof.proof_type == "manual_attestation":
        if (submitted_value or "").strip() != "I_AM_AUTHORIZED":
            return VerificationResult(
                ok=False,
                status="failed",
                message="Manual attestation proof must be I_AM_AUTHORIZED.",
                submitted_value=submitted_value,
            )
        return VerificationResult(
            ok=True,
            status="attested",
            message="Manual attestation recorded, but the target is not fully verified.",
            submitted_value=submitted_value,
        )

    if proof.expires_at and proof.expires_at < _now():
        return VerificationResult(
            ok=False,
            status="expired",
            message="Authorization challenge has expired. Issue a new challenge and try again.",
            submitted_value=submitted_value,
        )

    if proof.proof_type == "dns_txt":
        return await _verify_dns_txt(proof=proof, submitted_value=submitted_value)
    if proof.proof_type == "http_file":
        return await _verify_http_file(proof=proof, submitted_value=submitted_value)
    if proof.proof_type == "meta_tag":
        return await _verify_meta_tag(proof=proof, submitted_value=submitted_value)
    if proof.proof_type == "github_file":
        return await _verify_github_file(target=target, proof=proof, submitted_value=submitted_value)

    return VerificationResult(
        ok=False,
        status="failed",
        message=f"Unsupported proof type {proof.proof_type}.",
        submitted_value=submitted_value,
    )


async def _verify_dns_txt(*, proof: TargetAuthorizationProof, submitted_value: str | None) -> VerificationResult:
    if dns is None:
        return VerificationResult(
            ok=False,
            status="failed",
            message="dns verification requires the dnspython package to be installed.",
            submitted_value=submitted_value,
        )

    record_name = (submitted_value or proof.verification_target).strip()
    try:
        answers = await asyncio.wait_for(
            dns.resolve(record_name, "TXT"),
            timeout=settings.TARGET_AUTH_HTTP_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        return VerificationResult(
            ok=False,
            status="failed",
            message=f"Could not resolve DNS TXT records for {record_name}: {exc}",
            submitted_value=record_name,
        )

    values = {"".join(part.decode("utf-8") for part in answer.strings) for answer in answers}
    if proof.expected_value not in values:
        return VerificationResult(
            ok=False,
            status="failed",
            message=f"TXT record for {record_name} did not contain the expected challenge value.",
            submitted_value=record_name,
        )
    return VerificationResult(
        ok=True,
        status="verified",
        message=f"DNS TXT verification succeeded for {record_name}.",
        submitted_value=record_name,
    )


async def _verify_http_file(*, proof: TargetAuthorizationProof, submitted_value: str | None) -> VerificationResult:
    url = (submitted_value or proof.verification_target).strip()
    return await _fetch_exact_value(
        url=url,
        expected=proof.expected_value,
        success_message=f"HTTP file verification succeeded for {url}.",
        failure_message=f"Verification file at {url} did not contain the expected challenge value.",
    )


async def _verify_meta_tag(*, proof: TargetAuthorizationProof, submitted_value: str | None) -> VerificationResult:
    url = (submitted_value or proof.verification_target).strip()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=settings.TARGET_AUTH_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception as exc:
        return VerificationResult(
            ok=False,
            status="failed",
            message=f"Could not fetch {url} for meta-tag verification: {exc}",
            submitted_value=url,
        )

    html = response.text
    for name, content in re.findall(
        r"<meta\s+[^>]*name=[\"']([^\"']+)[\"'][^>]*content=[\"']([^\"']+)[\"'][^>]*>",
        html,
        flags=re.IGNORECASE,
    ):
        if name.strip().lower() == "armorscan-verification" and unescape(content.strip()) == proof.challenge_token:
            return VerificationResult(
                ok=True,
                status="verified",
                message=f"Meta-tag verification succeeded for {url}.",
                submitted_value=url,
            )

    return VerificationResult(
        ok=False,
        status="failed",
        message=f"Meta tag armorscan-verification was not found with the expected token on {url}.",
        submitted_value=url,
    )


async def _verify_github_file(
    *, target: Target, proof: TargetAuthorizationProof, submitted_value: str | None
) -> VerificationResult:
    url = (submitted_value or "").strip()
    slug = proof.metadata_json.get("repo_slug")
    if not url:
        return VerificationResult(
            ok=False,
            status="failed",
            message="GitHub file verification requires the raw GitHub file URL as proof.",
            submitted_value=submitted_value,
        )
    parsed = urlparse(url)
    if parsed.netloc.lower() != "raw.githubusercontent.com" or not slug or f"/{slug}/" not in parsed.path:
        return VerificationResult(
            ok=False,
            status="failed",
            message="Provided GitHub proof URL does not match the target repository raw file path.",
            submitted_value=url,
        )
    return await _fetch_exact_value(
        url=url,
        expected=proof.expected_value,
        success_message=f"GitHub file verification succeeded for {target.target_url}.",
        failure_message="The GitHub verification file did not contain the expected challenge value.",
    )


async def _fetch_exact_value(
    *, url: str, expected: str, success_message: str, failure_message: str
) -> VerificationResult:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=settings.TARGET_AUTH_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception as exc:
        return VerificationResult(
            ok=False,
            status="failed",
            message=f"Could not fetch verification content from {url}: {exc}",
            submitted_value=url,
        )

    content = response.text.strip()
    if content != expected:
        return VerificationResult(
            ok=False,
            status="failed",
            message=failure_message,
            submitted_value=url,
        )
    return VerificationResult(ok=True, status="verified", message=success_message, submitted_value=url)
