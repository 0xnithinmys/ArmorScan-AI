from __future__ import annotations

from html import unescape
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from armorscan.policy import evaluate_agent_action
from armorscan.tools.engine_common import EngineResult, normalize_severity, run_json_command


def _candidate_zap_install_dirs() -> list[Path]:
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    user_profile = os.environ.get("USERPROFILE", r"C:\Users\Nithin")
    return [
        Path(program_files) / "ZAP" / "Zed Attack Proxy",
        Path(program_files_x86) / "ZAP" / "Zed Attack Proxy",
        Path(user_profile) / "ZAP",
    ]


def _find_zap_runtime() -> dict[str, str] | None:
    baseline = shutil.which("zap-baseline.py") or shutil.which("zap-baseline")
    if baseline:
        return {"mode": "baseline-script", "launcher": baseline}

    java = shutil.which("java")
    if not java:
        java = (
            Path(r"C:\Program Files\Eclipse Adoptium\jre-17.0.19.10-hotspot\bin\java.exe")
            if Path(r"C:\Program Files\Eclipse Adoptium\jre-17.0.19.10-hotspot\bin\java.exe").exists()
            else None
        )
        if java is not None:
            java = str(java)

    for install_dir in _candidate_zap_install_dirs():
        jar = next(install_dir.glob("zap-*.jar"), None)
        if jar is not None and java:
            return {
                "mode": "jar",
                "java": java,
                "jar": str(jar),
                "install_dir": str(install_dir),
            }
        zap_bat = install_dir / "zap.bat"
        if zap_bat.exists():
            # Use the batch launcher if Java is already on PATH.
            if shutil.which("java"):
                return {"mode": "bat", "launcher": str(zap_bat)}
    return None


def _clean_zap_text(value: Any) -> str:
    text = unescape(str(value or "")).strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_zap_alert(alert: dict[str, Any], target_url: str) -> dict[str, Any]:
    risk = str(alert.get("riskcode") or alert.get("risk") or "0").lower()
    severity_map = {"3": "high", "2": "medium", "1": "low", "0": "info", "high": "high", "medium": "medium", "low": "low", "informational": "info"}
    instances = alert.get("instances") or []
    instance = instances[0] if instances else {}
    location = instance.get("uri") or target_url
    summary = _clean_zap_text(alert.get("desc") or alert.get("description") or alert.get("name"))
    solution = _clean_zap_text(alert.get("solution") or alert.get("otherinfo"))
    return {
        "id": f"zap-{alert.get('pluginid') or alert.get('pluginId') or alert.get('name', 'alert')}",
        "title": alert.get("name") or "OWASP ZAP alert",
        "severity": severity_map.get(risk, normalize_severity(risk)),
        "cwe_id": alert.get("cweid") or None,
        "location": location,
        "parameter": instance.get("param"),
        "payload": instance.get("attack"),
        "evidence": instance.get("evidence") or _clean_zap_text(alert.get("otherinfo") or alert.get("desc")),
        "confidence": 83,
        "summary": summary or "OWASP ZAP detected a passive or baseline scan issue.",
        "remediation": solution or None,
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

    runtime = _find_zap_runtime()
    if not runtime:
        result.errors.append("OWASP ZAP is not installed or could not be located")
        result.observations.append(
            {
                "engine": "owasp-zap",
                "available": False,
                "message": "Install OWASP ZAP and Java 17+, or put zap-baseline.py on PATH.",
            }
        )
        return result

    result.available = True
    report_path = Path(tempfile.gettempdir()) / "armorscan-zap-report.json"
    zap_home = Path(tempfile.mkdtemp(prefix="armorscan-zap-home-"))
    if runtime["mode"] == "baseline-script":
        args = [runtime["launcher"], "-t", target_url, "-J", str(report_path), "-m", "3"]
    else:
        args = [
            runtime["java"],
            "-jar",
            runtime["jar"],
            "-dir",
            str(zap_home),
            "-cmd",
            "-quickurl",
            target_url,
            "-quickout",
            str(report_path),
            "-silent",
            "-notel",
        ]
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
                "launcher_mode": runtime["mode"],
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
        if "zap_home" in locals() and zap_home.exists():
            try:
                shutil.rmtree(zap_home)
            except OSError:
                pass
    return result
