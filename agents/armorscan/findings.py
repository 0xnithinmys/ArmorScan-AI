from __future__ import annotations

import hashlib
from typing import Any


SEVERITIES = {"critical", "high", "medium", "low", "info"}


def normalize_severity(value: Any) -> str:
    severity = str(value or "info").lower()
    return severity if severity in SEVERITIES else "info"


def clamp_confidence(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 50
    if number <= 1:
        number *= 100
    return max(0, min(100, round(number)))


def finding_fingerprint(finding: dict[str, Any]) -> str:
    raw = "|".join(
        str(finding.get(key) or "").strip().lower()
        for key in ("title", "location", "parameter", "payload", "source")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalize_finding(finding: dict[str, Any], *, default_source: str = "agent") -> dict[str, Any]:
    location = finding.get("location") or finding.get("url") or finding.get("path") or "unknown"
    title = str(finding.get("title") or "Untitled finding").strip()[:255]
    summary = str(finding.get("summary") or finding.get("rationale") or title).strip()
    normalized = {
        "id": str(finding.get("id") or ""),
        "title": title,
        "severity": normalize_severity(finding.get("severity")),
        "cwe_id": finding.get("cwe_id"),
        "location": str(location),
        "parameter": finding.get("parameter"),
        "payload": finding.get("payload"),
        "evidence": finding.get("evidence"),
        "confidence": clamp_confidence(finding.get("confidence", 50)),
        "summary": summary,
        "reproduction_steps": list(finding.get("reproduction_steps") or []),
        "source": finding.get("source") or default_source,
    }
    if not normalized["id"]:
        normalized["id"] = f"{normalized['source']}-{finding_fingerprint(normalized)}"
    normalized["fingerprint"] = finding_fingerprint(normalized)
    return normalized


def dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_fingerprint: dict[str, dict[str, Any]] = {}
    for item in findings:
        finding = normalize_finding(item)
        current = by_fingerprint.get(finding["fingerprint"])
        if current is None or finding["confidence"] > current["confidence"]:
            by_fingerprint[finding["fingerprint"]] = finding
    return sorted(
        by_fingerprint.values(),
        key=lambda finding: (
            {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}[finding["severity"]],
            finding["confidence"],
        ),
        reverse=True,
    )


def normalize_draft(draft: dict[str, Any], *, fallback_url: str) -> dict[str, Any] | None:
    if not draft.get("title"):
        return None
    confidence = clamp_confidence(draft.get("confidence", 50))
    if confidence < 35:
        return None
    return {
        "id": draft.get("id"),
        "title": draft["title"],
        "severity": normalize_severity(draft.get("severity")),
        "cwe_id": draft.get("cwe_id"),
        "location": draft.get("url") or fallback_url,
        "parameter": draft.get("parameter"),
        "payload": draft.get("payload"),
        "evidence": draft.get("evidence"),
        "confidence": confidence,
        "summary": draft.get("rationale") or draft["title"],
        "reproduction_steps": list(draft.get("reproduction_steps") or []),
        "source": "agent-analysis",
    }
