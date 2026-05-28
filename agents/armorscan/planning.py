from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from armorscan.utils import normalize_target_url


def _host(value: str) -> str:
    parsed = urlparse(normalize_target_url(value))
    return parsed.hostname or parsed.path or value


def build_scan_plan(state: dict[str, Any]) -> dict[str, Any]:
    scan_type = state["scan_type"]
    target_url = state["target_url"]
    intent_plan = state.get("intent_plan") or {}
    allowed_actions = set(intent_plan.get("allowed_actions", []))
    target_host = _host(target_url)

    phases = [
        {
            "name": "passive_recon",
            "goal": "Map public routes, inputs, browser-rendered controls, and low-risk metadata.",
            "actions": sorted({"http.get", "browser.navigate"} & allowed_actions),
            "safety": "Read-only requests inside signed scope.",
        },
        {
            "name": "scanner_engines",
            "goal": "Run available DAST/SAST engines and normalize evidence.",
            "actions": sorted(
                {"scanner.nuclei", "scanner.zap", "scanner.semgrep", "scanner.bandit", "scanner.gitleaks", "scanner.trivy"}
                & allowed_actions
            ),
            "safety": "No destructive templates, no off-scope hosts, CLI absence becomes a non-fatal observation.",
        },
        {
            "name": "analysis",
            "goal": "Correlate recon and scanner evidence into candidate vulnerabilities.",
            "actions": [],
            "safety": "Reason over evidence only; do not invent exploit paths.",
        },
        {
            "name": "safe_validation",
            "goal": "Confirm only harmless reflected probes already covered by policy.",
            "actions": sorted({"http.get"} & allowed_actions),
            "safety": "Payload markers and host scope are checked before every probe.",
        },
        {
            "name": "reporting",
            "goal": "Produce a prioritized evidence bundle with reproducible steps.",
            "actions": [],
            "safety": "Preserve traceability from finding to observation.",
        },
    ]

    if scan_type == "github":
        phases[0]["goal"] = "Resolve local repository path and collect non-network static context."
        phases[1]["goal"] = "Run Semgrep/Bandit/Gitleaks/Trivy or deterministic fallback rules against repository source."
    elif scan_type == "api":
        phases[0]["goal"] = "Map public API routes, metadata, and lightweight response behavior."

    return {
        "target": target_url,
        "target_host": target_host,
        "scan_type": scan_type,
        "mode": "governed-passive-plus-safe-validation",
        "allowed_actions": sorted(allowed_actions),
        "allowed_hosts": intent_plan.get("allowed_hosts", []),
        "limits": intent_plan.get("limits", {}),
        "phases": phases,
        "success_criteria": [
            "Every network or browser action has a policy decision.",
            "Scanner and LLM findings are normalized into one schema.",
            "Reports include evidence, confidence, risk-ready metadata, and reproduction steps.",
            "Failures become trace entries rather than silent drops.",
        ],
    }
