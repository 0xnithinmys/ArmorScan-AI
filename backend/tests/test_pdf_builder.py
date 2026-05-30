from __future__ import annotations

from app.services.pdf_builder import generate_pdf_report


def test_generate_pdf_report_returns_real_pdf_bytes() -> None:
    report = {
        "target": {"target_url": "https://example.com"},
        "executive_summary": {
            "overall_risk_rating": "medium",
            "overall_risk_score": 64,
            "narrative": "ArmorScan assigned an overall medium risk rating based on 1 confirmed findings.",
        },
        "findings": [
            {
                "title": "Content Security Policy (CSP) Header Not Set",
                "risk_rating": "medium",
                "risk_score": 64,
                "location": "https://example.com",
                "confidence": 89,
                "summary": "OWASP ZAP detected a passive or baseline scan issue.",
                "business_impact": "Meaningful risk",
                "remediation": "Set a CSP header.",
            }
        ],
    }

    pdf = generate_pdf_report(report)

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000
