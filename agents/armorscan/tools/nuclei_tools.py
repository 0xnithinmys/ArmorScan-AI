from __future__ import annotations

import shutil
from typing import Any

from armorscan.policy import evaluate_agent_action
from armorscan.tools.engine_common import EngineResult, normalize_severity, parse_json_lines, run_json_command


def _normalize_nuclei_finding(row: dict[str, Any], target_url: str) -> dict[str, Any]:
    info = row.get("info") or {}
    template_id = row.get("template-id") or row.get("templateID") or "nuclei-template"
    matched_at = row.get("matched-at") or row.get("host") or target_url
    return {
        "id": f"nuclei-{template_id}",
        "title": info.get("name") or template_id,
        "severity": normalize_severity(info.get("severity")),
        "cwe_id": None,
        "location": matched_at,
        "parameter": None,
        "payload": row.get("matcher-name"),
        "evidence": row.get("extracted-results") or row.get("curl-command") or row.get("matcher-name"),
        "confidence": 88,
        "summary": info.get("description") or f"Nuclei matched template {template_id}.",
        "reproduction_steps": [
            f"Run nuclei against {target_url} with template {template_id}.",
            f"Review matched endpoint: {matched_at}.",
        ],
        "source": "nuclei",
        "raw": row,
    }


async def run_nuclei_scan(
    target_url: str,
    *,
    intent_plan: dict[str, Any] | None,
    token: str | None,
) -> EngineResult:
    result = EngineResult(engine="nuclei", available=False)
    decision = evaluate_agent_action(
        intent_plan=intent_plan,
        token=token,
        action="scanner.nuclei",
        url=target_url,
    )
    result.policy_decisions.append(decision.as_dict())
    if not decision.allowed:
        result.errors.append(decision.reason)
        result.observations.append({"engine": "nuclei", "blocked_by_policy": decision.reason})
        return result

    binary = shutil.which("nuclei")
    if not binary:
        result.errors.append("nuclei CLI is not installed or not on PATH")
        result.observations.append(
            {
                "engine": "nuclei",
                "available": False,
                "message": "Install nuclei to enable template-based DAST findings.",
            }
        )
        return result

    result.available = True
    args = [
        binary,
        "-u",
        target_url,
        "-jsonl",
        "-silent",
        "-severity",
        "low,medium,high,critical",
        "-rate-limit",
        "25",
        "-timeout",
        "5",
    ]
    try:
        return_code, stdout, stderr = await run_json_command(args, timeout_seconds=120)
        rows = parse_json_lines(stdout)
        result.findings.extend(_normalize_nuclei_finding(row, target_url) for row in rows)
        result.observations.append(
            {
                "engine": "nuclei",
                "available": True,
                "return_code": return_code,
                "templates_matched": len(rows),
            }
        )
        if stderr.strip():
            result.errors.append(stderr.strip()[:1000])
    except TimeoutError:
        result.errors.append("nuclei scan timed out")
    except Exception as exc:
        result.errors.append(str(exc))
    return result
