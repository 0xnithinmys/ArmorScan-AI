from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


SEVERITY_BASE = {
    "critical": 95,
    "high": 80,
    "medium": 55,
    "low": 30,
    "info": 10,
}
RATING_BANDS = [
    (90, "critical"),
    (70, "high"),
    (40, "medium"),
    (15, "low"),
    (0, "info"),
]
CONTEXT_KEYWORDS = {
    "admin": 8,
    "login": 6,
    "auth": 6,
    "password": 6,
    "payment": 8,
    "billing": 8,
    "api": 4,
    "graphql": 5,
    "token": 6,
}
SOURCE_MODIFIERS = {
    "nuclei": 4,
    "owasp-zap": 4,
    "semgrep": 2,
    "bandit": 2,
    "gitleaks": 4,
    "trivy": 3,
    "semgrep-fallback": -5,
    "bandit-fallback": -5,
}

OWASP_CATEGORY_MAP = {
    "CWE-79": "A03:2021 - Injection",
    "CWE-78": "A03:2021 - Injection",
    "CWE-89": "A03:2021 - Injection",
    "CWE-95": "A03:2021 - Injection",
    "CWE-200": "A01:2021 - Broken Access Control",
    "CWE-287": "A07:2021 - Identification and Authentication Failures",
    "CWE-295": "A02:2021 - Cryptographic Failures",
    "CWE-502": "A08:2021 - Software and Data Integrity Failures",
    "CWE-798": "A07:2021 - Identification and Authentication Failures",
    "CWE-942": "A05:2021 - Security Misconfiguration",
    "CWE-693": "A05:2021 - Security Misconfiguration",
}


def _clamp(value: int, lower: int = 0, upper: int = 100) -> int:
    return max(lower, min(upper, value))


def risk_rating(score: int) -> str:
    for threshold, rating in RATING_BANDS:
        if score >= threshold:
            return rating
    return "info"


def _text_for(finding: dict[str, Any]) -> str:
    return " ".join(
        str(finding.get(key, ""))
        for key in ("title", "location", "summary", "evidence", "parameter", "payload")
    ).lower()


def _context_modifier(finding: dict[str, Any]) -> int:
    text = _text_for(finding)
    modifier = 0
    for keyword, weight in CONTEXT_KEYWORDS.items():
        if keyword in text:
            modifier = max(modifier, weight)
    return modifier


def _exploitability_modifier(finding: dict[str, Any]) -> int:
    text = _text_for(finding)
    modifier = 0
    if finding.get("payload"):
        modifier += 4
    if "reflected" in text or "matched" in text or "confirmed" in text:
        modifier += 5
    if "fallback" in str(finding.get("source", "")):
        modifier -= 5
    return modifier


def remediation_for(finding: dict[str, Any]) -> str:
    text = _text_for(finding)
    if "xss" in text or "cwe-79" in text or "innerhtml" in text:
        return "Encode untrusted output, prefer safe DOM APIs, and enforce a strict Content Security Policy."
    if "shell" in text or "command" in text or "cwe-78" in text:
        return "Avoid shell execution, pass arguments as arrays, and validate all command inputs against allowlists."
    if "secret" in text or "api_key" in text or "password" in text:
        return "Move secrets to a managed secret store, rotate exposed values, and add secret scanning to CI."
    if "tls" in text or "verify=false" in text:
        return "Require certificate validation and remove insecure TLS bypasses from production code paths."
    if "admin" in text:
        return "Require authentication and authorization on administrative routes, and add monitoring for access attempts."
    if "header" in text or "fingerprint" in text:
        return "Reduce technology-disclosing headers and validate that debug metadata is disabled in production."
    return "Validate exploitability, identify the affected trust boundary, and prioritize a targeted code or configuration fix."


def score_finding(finding: dict[str, Any]) -> dict[str, Any]:
    severity = str(finding.get("severity", "info")).lower()
    confidence = int(finding.get("confidence") or 0)
    source = str(finding.get("source") or "").lower()
    base = SEVERITY_BASE.get(severity, SEVERITY_BASE["info"])
    confidence_modifier = round((confidence - 70) * 0.25)
    context_modifier = _context_modifier(finding)
    exploitability_modifier = _exploitability_modifier(finding)
    source_modifier = SOURCE_MODIFIERS.get(source, 0)
    score = _clamp(base + confidence_modifier + context_modifier + exploitability_modifier + source_modifier)
    rating = risk_rating(score)
    scored = dict(finding)
    scored.update(
        {
            "risk_score": score,
            "risk_rating": rating,
            "owasp_category": map_owasp_category(finding),
            "risk_factors": {
                "severity_base": base,
                "confidence_modifier": confidence_modifier,
                "context_modifier": context_modifier,
                "exploitability_modifier": exploitability_modifier,
                "source_modifier": source_modifier,
            },
            "business_impact": business_impact_for(rating),
            "remediation": scored_remediation(finding),
        }
    )
    return scored


def map_owasp_category(finding: dict[str, Any]) -> str | None:
    cwe_id = str(finding.get("cwe_id") or "").upper()
    if cwe_id and cwe_id in OWASP_CATEGORY_MAP:
        return OWASP_CATEGORY_MAP[cwe_id]
    text = _text_for(finding)
    if "secret" in text or "token" in text or "password" in text:
        return "A07:2021 - Identification and Authentication Failures"
    if "header" in text or "csp" in text or "cors" in text or "misconfig" in text:
        return "A05:2021 - Security Misconfiguration"
    if "dependency" in text or "vulnerab" in text:
        return "A06:2021 - Vulnerable and Outdated Components"
    return None


def scored_remediation(finding: dict[str, Any]) -> str:
    return str(finding.get("remediation") or remediation_for(finding))


def business_impact_for(rating: str) -> str:
    if rating == "critical":
        return "Likely direct compromise path or high-impact exposure requiring immediate owner attention."
    if rating == "high":
        return "Material security weakness that should be scheduled for near-term remediation."
    if rating == "medium":
        return "Meaningful risk that needs triage, validation, and backlog prioritization."
    if rating == "low":
        return "Low-impact hardening opportunity with limited immediate exploitability."
    return "Informational observation useful for asset inventory or follow-up analysis."


def enrich_findings_with_risk(findings: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((score_finding(finding) for finding in findings), key=lambda item: item["risk_score"], reverse=True)


def build_risk_summary(findings: Iterable[dict[str, Any]]) -> dict[str, Any]:
    scored = enrich_findings_with_risk(findings)
    counts: dict[str, int] = {rating: 0 for _, rating in RATING_BANDS}
    for finding in scored:
        counts[finding["risk_rating"]] = counts.get(finding["risk_rating"], 0) + 1
    top_score = scored[0]["risk_score"] if scored else 0
    return {
        "overall_risk_score": top_score,
        "overall_risk_rating": risk_rating(top_score),
        "risk_counts": counts,
        "top_findings": scored[:5],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_risk_report(*, scan: dict[str, Any], target: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    scored_findings = enrich_findings_with_risk(findings)
    summary = build_risk_summary(scored_findings)
    owasp_categories: dict[str, int] = {}
    for finding in scored_findings:
        category = finding.get("owasp_category")
        if category:
            owasp_categories[category] = owasp_categories.get(category, 0) + 1
    return {
        "version": "armorscan.report.v1",
        "scan": scan,
        "target": target,
        "executive_summary": {
            "overall_risk_score": summary["overall_risk_score"],
            "overall_risk_rating": summary["overall_risk_rating"],
            "risk_counts": summary["risk_counts"],
            "owasp_top10_coverage": owasp_categories,
            "narrative": _executive_narrative(summary),
        },
        "findings": scored_findings,
        "prioritized_actions": [
            {
                "finding_id": finding.get("id"),
                "title": finding.get("title"),
                "risk_score": finding.get("risk_score"),
                "remediation": finding.get("remediation"),
            }
            for finding in scored_findings[:5]
        ],
        "generated_at": summary["generated_at"],
    }


def _executive_narrative(summary: dict[str, Any]) -> str:
    rating = summary["overall_risk_rating"]
    count = sum(summary["risk_counts"].values())
    if count == 0:
        return "No confirmed findings were available for risk scoring."
    return f"ArmorScan assigned an overall {rating} risk rating based on {count} confirmed findings."


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# ArmorScan AI Security Report",
        "",
        f"Target: {report['target'].get('target_url') or report['target'].get('url')}",
        f"Overall risk: {report['executive_summary']['overall_risk_rating']} ({report['executive_summary']['overall_risk_score']}/100)",
        "",
        "## Executive Summary",
        report["executive_summary"]["narrative"],
        "",
        "## Prioritized Findings",
    ]
    for finding in report["findings"]:
        lines.extend(
            [
                "",
                f"### {finding.get('title')}",
                f"- Risk: {finding.get('risk_rating')} ({finding.get('risk_score')}/100)",
                f"- Severity: {finding.get('severity')} | Confidence: {finding.get('confidence')}%",
                f"- Location: {finding.get('location')}",
                f"- OWASP: {finding.get('owasp_category') or 'unmapped'}",
                f"- Impact: {finding.get('business_impact')}",
                f"- Remediation: {finding.get('remediation')}",
            ]
        )
    return "\n".join(lines) + "\n"


def render_pdf_report(report: dict[str, Any]) -> bytes:
    text = render_markdown_report(report)
    lines = []
    for raw_line in text.replace("#", "").splitlines():
        line = raw_line.strip()
        if line:
            lines.append(line[:96])
    return _simple_pdf(lines[:45])


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _simple_pdf(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index:
            content_lines.append("T*")
        content_lines.append(f"({_pdf_escape(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)
