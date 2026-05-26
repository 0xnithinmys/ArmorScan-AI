from __future__ import annotations

import asyncio
from typing import Any

from armorscan.tools.nuclei_tools import run_nuclei_scan
from armorscan.tools.sast_tools import run_bandit_scan, run_semgrep_scan


async def run_scanning_engines(state: dict[str, Any]) -> dict[str, Any]:
    scan_type = state["scan_type"]
    target = state["target_url"]
    intent_plan = state.get("intent_plan")
    token = state.get("armoriq_token")

    tasks = []
    if scan_type in {"url", "api"}:
        tasks.append(run_nuclei_scan(target, intent_plan=intent_plan, token=token))
    if scan_type == "github":
        tasks.extend(
            [
                run_semgrep_scan(target, intent_plan=intent_plan, token=token),
                run_bandit_scan(target, intent_plan=intent_plan, token=token),
            ]
        )

    if not tasks:
        return {
            "engine_observations": [],
            "engine_findings": [],
            "engine_errors": [f"No scanner engines are mapped for scan type {scan_type}"],
            "policy_decisions": [],
        }

    results = await asyncio.gather(*tasks)
    observations: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    errors: list[str] = []
    policy_decisions: list[dict[str, Any]] = []

    for result in results:
        observations.extend(result.observations)
        findings.extend(result.findings)
        errors.extend(f"{result.engine}: {error}" for error in result.errors)
        policy_decisions.extend(result.policy_decisions)

    return {
        "engine_observations": observations,
        "engine_findings": findings,
        "engine_errors": errors,
        "policy_decisions": policy_decisions,
    }
