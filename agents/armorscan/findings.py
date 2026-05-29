from __future__ import annotations

import hashlib
import re
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
    location = _canonical_location(str(finding.get("location") or ""))
    weakness = _weakness_key(finding)
    raw = "|".join(
        [
            weakness,
            location,
            str(finding.get("parameter") or "").strip().lower(),
            str(finding.get("payload") or "").strip().lower(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _canonical_location(location: str) -> str:
    value = location.replace("\\", "/").strip()
    value = re.sub(r"https://github\.com/[^/]+/[^/]+/blob/[^/]+/", "", value)
    value = re.sub(r"#L(\d+)$", r":\1", value)
    value = re.sub(r":+", ":", value)
    return value.lower()


def _weakness_key(finding: dict[str, Any]) -> str:
    text = " ".join(
        str(finding.get(key) or "")
        for key in ("id", "title", "summary", "evidence", "cwe_id")
    ).lower()
    if "eval" in text:
        return "dynamic-code-eval"
    if "exec" in text:
        return "dynamic-code-exec"
    if "shell=true" in text or "shell = true" in text or "cwe-78" in text:
        return "os-command-shell"
    if "secret" in text or "api_key" in text or "token" in text or "cwe-798" in text:
        return "hardcoded-secret"
    if "pickle" in text or "yaml.load" in text or "cwe-502" in text:
        return "unsafe-deserialization"
    return str(finding.get("cwe_id") or finding.get("title") or "finding").strip().lower()


def _merge_findings(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    severity_rank = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
    primary = incoming if (
        severity_rank[incoming["severity"]] > severity_rank[current["severity"]]
        or incoming["confidence"] > current["confidence"]
    ) else current
    secondary = current if primary is incoming else incoming
    merged = dict(primary)
    sources = set(primary.get("correlated_sources") or [primary.get("source") or "agent"])
    sources.update(secondary.get("correlated_sources") or [secondary.get("source") or "agent"])
    evidence = [item for item in [primary.get("evidence"), secondary.get("evidence")] if item]
    steps = list(dict.fromkeys((primary.get("reproduction_steps") or []) + (secondary.get("reproduction_steps") or [])))
    merged["correlated_sources"] = sorted(str(source) for source in sources if source)
    if evidence:
        merged["evidence"] = "\n\n".join(dict.fromkeys(str(item) for item in evidence))[:2000]
    merged["reproduction_steps"] = steps[:8]
    merged["confidence"] = max(primary["confidence"], secondary["confidence"])
    return merged


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
        if current is None:
            by_fingerprint[finding["fingerprint"]] = finding
        else:
            by_fingerprint[finding["fingerprint"]] = _merge_findings(current, finding)
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
