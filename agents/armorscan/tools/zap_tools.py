from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from armorscan.policy import evaluate_agent_action
from armorscan.tools.engine_common import EngineResult, normalize_severity, run_json_command


def _normalize_zap_alert(alert: dict[str, Any], target_url: str) -> dict[str, Any]:
    risk = str(alert.get("riskcode") or alert.get("risk") or "0").lower()
    severity_map = {"3": "high", "2": "medium", "1": "low", "0": "info", "high": "high", "medium": "medium", "low": "low", "informational": "info"}
    instances = alert.get("instances") or []
    instance = instances[0] if instances else {}
    location = instance.get("uri") or target_url
    return {
        "id": f"zap-{alert.get('pluginid') or alert.get('pluginId') or alert.get('name', 'alert')}",
        "title": alert.get("name") or "OWASP ZAP alert",
        "severity": severity_map.get(risk, normalize_severity(risk)),
        "cwe_id": alert.get("cweid") or None,
        "location": location,
        "parameter": instance.get("param"),
        "payload": instance.get("attack"),
        "evidence": instance.get("evidence") or alert.get("description"),
        "confidence": 83,
        "summary": alert.get("description") or "OWASP ZAP detected a passive or baseline scan issue.",
        "reproduction_steps": [
            f"Run OWASP ZAP baseline scan against {target_url}.",
            f"Review the alert details for {location}.",
        ],
        "source": "owasp-zap",
        "raw": alert,
    }


async def run_zap_baseline_scan(
    target_url: str,
    *,
    intent_plan: dict[str, Any] | None,
    token: str | None,
) -> EngineResult:
    result = EngineResult(engine="owasp-zap", available=False)
    decision = evaluate_agent_action(
        intent_plan=intent_plan,
        token=token,
        action="scanner.zap",
        url=target_url,
    )
    result.policy_decisions.append(decision.as_dict())
    if not decision.allowed:
        result.errors.append(decision.reason)
        result.observations.append({"engine": "owasp-zap", "blocked_by_policy": decision.reason})
        return result

    binary = shutil.which("zap-baseline.py") or shutil.which("zap-baseline")
    if not binary:
        result.errors.append("OWASP ZAP baseline script is not installed or not on PATH")
        result.observations.append(
            {
                "engine": "owasp-zap",
                "available": False,
                "message": "Install OWASP ZAP baseline to enable passive spidering and alert normalization.",
            }
        )
        return result

    result.available = True
    report_path = Path(tempfile.gettempdir()) / "armorscan-zap-report.json"
    args = [binary, "-t", target_url, "-J", str(report_path), "-m", "3"]
    try:
        return_code, stdout, stderr = await run_json_command(args, timeout_seconds=300)
        findings: list[dict[str, Any]] = []
        if report_path.exists():
            data = json.loads(report_path.read_text(encoding="utf-8", errors="ignore") or "{}")
            for site in data.get("site") or []:
                for alert in site.get("alerts") or []:
                    findings.append(_normalize_zap_alert(alert, target_url))
        result.findings.extend(findings)
        result.observations.append(
            {
                "engine": "owasp-zap",
                "available": True,
                "return_code": return_code,
                "alerts": len(findings),
            }
        )
        if stderr.strip():
            result.errors.append(stderr.strip()[:1000])
    except TimeoutError:
        result.errors.append("OWASP ZAP baseline scan timed out")
    except Exception as exc:
        result.errors.append(str(exc))
    finally:
        if report_path.exists():
            try:
                report_path.unlink()
            except OSError:
                pass
    return result
