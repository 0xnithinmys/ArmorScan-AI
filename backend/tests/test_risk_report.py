from __future__ import annotations

from app.services.risk import build_risk_report


def test_zap_findings_get_specific_summary_and_remediation() -> None:
    report = build_risk_report(
        scan={"id": "scan-1", "status": "completed", "scan_type": "url"},
        target={"id": "target-1", "target_url": "https://example.com"},
        findings=[
            {
                "id": "zap-10038",
                "title": "Content Security Policy (CSP) Header Not Set",
                "severity": "medium",
                "location": "https://example.com",
                "confidence": 89,
                "summary": "OWASP ZAP detected a passive or baseline scan issue.",
                "business_impact": None,
                "remediation": None,
                "risk_factors": {},
                "reproduction_steps": [],
                "source": "owasp-zap",
            }
        ],
    )

    finding = report["findings"][0]

    assert "content security policy" in finding["summary"].lower()
    assert "csp" in finding["remediation"].lower() or "content-security-policy" in finding["remediation"].lower()
