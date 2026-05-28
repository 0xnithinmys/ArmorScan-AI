from __future__ import annotations

from collections import Counter
from typing import Any


def build_evidence_summary(state: dict[str, Any]) -> dict[str, Any]:
    policy_counter = Counter("allowed" if item.get("allowed") else "blocked" for item in state.get("policy_decisions", []))
    engine_counter = Counter(
        str(obs.get("engine") or "unknown")
        for obs in state.get("engine_observations", [])
    )
    finding_counter = Counter(
        str(finding.get("severity") or "info")
        for finding in state.get("findings", [])
    )
    return {
        "coverage": {
            "routes": len(state.get("discovered_routes", [])),
            "forms": len(state.get("discovered_forms", [])),
            "inputs": len(state.get("discovered_inputs", [])),
            "browser_observations": len(state.get("browser_observations", [])),
            "http_observations": len(state.get("http_observations", [])),
            "engine_observations": len(state.get("engine_observations", [])),
        },
        "policy": {
            "allowed": policy_counter.get("allowed", 0),
            "blocked": policy_counter.get("blocked", 0),
            "total": len(state.get("policy_decisions", [])),
        },
        "engines": dict(engine_counter),
        "findings_by_severity": dict(finding_counter),
        "errors": {
            "browser": state.get("browser_errors", []),
            "engines": state.get("engine_errors", []),
            "workflow": state.get("error"),
        },
    }
