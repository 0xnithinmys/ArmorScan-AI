from __future__ import annotations

from armorscan.runtime import draft_has_evidence, fallback_analysis


def _base_state() -> dict:
    return {
        "scan_id": "scan-1",
        "target_url": "https://portfolio.example",
        "scan_type": "url",
        "status": "observing",
        "scan_plan": None,
        "discovered_routes": [],
        "discovered_forms": [],
        "discovered_inputs": [],
        "discovered_apis": [],
        "discovered_uploads": [],
        "discovered_js_endpoints": [],
        "authenticated_workflows": [],
        "repo_inventory": [],
        "dependency_inventory": [],
        "iac_inventory": [],
        "browser_observations": [],
        "browser_errors": [],
        "technology_stack": [],
        "state_graph": None,
        "engine_observations": [],
        "engine_findings": [],
        "engine_errors": [],
        "scanner_capabilities": [],
        "normalized_evidence": [],
        "correlation_summary": None,
        "retest_plan": None,
        "evidence_summary": None,
        "intent_plan": None,
        "armoriq_token": None,
        "policy_decisions": [],
        "http_observations": [
            {
                "url": "https://portfolio.example",
                "status_code": 200,
                "headers": {
                    "content-security-policy": "default-src 'self'",
                    "content-type": "text/html; charset=utf-8",
                },
                "body_excerpt": "<html>Welcome to my portfolio</html>",
            }
        ],
        "findings_drafts": [],
        "findings": [],
        "report_json": None,
        "agent_trace": [],
        "error": None,
    }


def test_fallback_analysis_does_not_invent_admin_surface_from_body_text_only() -> None:
    state = _base_state()
    state["http_observations"][0]["body_excerpt"] = "This portfolio mentions admin in prose, not in a route."

    findings = fallback_analysis(state)

    assert all(item["id"] != "admin-surface" for item in findings)


def test_fallback_analysis_requires_a_real_search_control() -> None:
    state = _base_state()
    state["discovered_routes"] = ["https://portfolio.example/search"]

    findings = fallback_analysis(state)
    assert all(item["id"] != "reflected-input-check" for item in findings)

    state["discovered_inputs"] = [
        {
            "tag": "input",
            "type": "search",
            "name": "q",
            "id": "site-search",
            "placeholder": "Search projects",
            "aria_label": "Search",
            "autocomplete": "off",
            "role": None,
            "purpose": "search",
        }
    ]

    findings = fallback_analysis(state)
    assert any(item["id"] == "reflected-input-check" for item in findings)


def test_draft_gate_rejects_invented_admin_and_search_findings() -> None:
    state = _base_state()

    admin_draft = {
        "title": "Administrative route exposed in public attack surface",
        "url": "https://portfolio.example/admin",
        "parameter": None,
    }
    search_draft = {
        "title": "Reflected input surface requires XSS validation",
        "url": "https://portfolio.example/search?q=probe",
        "parameter": "q",
    }

    assert draft_has_evidence(admin_draft, state) is False
    assert draft_has_evidence(search_draft, state) is False

    state["discovered_routes"] = ["https://portfolio.example/admin"]
    state["discovered_inputs"] = [
        {
            "tag": "input",
            "type": "search",
            "name": "q",
            "id": "site-search",
            "placeholder": "Search projects",
            "aria_label": "Search",
            "autocomplete": "off",
            "role": None,
            "purpose": "search",
        }
    ]

    assert draft_has_evidence(admin_draft, state) is True
    assert draft_has_evidence(search_draft, state) is True
