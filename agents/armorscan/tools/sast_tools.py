from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from armorscan.policy import evaluate_agent_action
from armorscan.tools.engine_common import EngineResult, normalize_severity, resolve_local_repo, run_json_command


STATIC_PATTERNS = [
    ("python-shell-true", re.compile(r"shell\s*=\s*True"), "high", "CWE-78", "Python subprocess uses shell=True"),
    ("python-eval", re.compile(r"\beval\s*\("), "high", "CWE-95", "Python eval() executes dynamic code"),
    ("python-exec", re.compile(r"\bexec\s*\("), "high", "CWE-95", "Python exec() executes dynamic code"),
    ("python-pickle", re.compile(r"pickle\.loads?\s*\("), "medium", "CWE-502", "Pickle deserialization detected"),
    ("python-yaml-load", re.compile(r"yaml\.load\s*\("), "medium", "CWE-502", "yaml.load() may deserialize unsafe data"),
    ("tls-verify-false", re.compile(r"verify\s*=\s*False"), "medium", "CWE-295", "TLS certificate verification disabled"),
    ("js-eval", re.compile(r"\beval\s*\("), "high", "CWE-95", "JavaScript eval() executes dynamic code"),
    ("js-inner-html", re.compile(r"(innerHTML\s*=|dangerouslySetInnerHTML)"), "medium", "CWE-79", "Raw HTML injection sink detected"),
    ("hardcoded-secret", re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"), "medium", "CWE-798", "Possible hardcoded secret"),
]
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _static_fallback(repo_path: Path, *, engine: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for file_path in repo_path.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        if any(part in {".git", "node_modules", ".venv", "__pycache__"} for part in file_path.parts):
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern_id, pattern, severity, cwe_id, title in STATIC_PATTERNS:
            for match in pattern.finditer(text):
                line = _line_for_offset(text, match.start())
                rel = file_path.relative_to(repo_path)
                findings.append(
                    {
                        "id": f"{engine}-fallback-{pattern_id}-{len(findings) + 1}",
                        "title": title,
                        "severity": severity,
                        "cwe_id": cwe_id,
                        "location": f"{rel}:{line}",
                        "parameter": None,
                        "payload": None,
                        "evidence": match.group(0)[:300],
                        "confidence": 72,
                        "summary": f"Fallback static scanner detected {title.lower()} in {rel}.",
                        "reproduction_steps": [
                            f"Open {rel} at line {line}.",
                            "Review whether user-controlled data can reach this sink or secret value.",
                        ],
                        "source": f"{engine}-fallback",
                    }
                )
                break
    return findings[:50]


def _normalize_semgrep(row: dict[str, Any], repo_path: Path) -> dict[str, Any]:
    extra = row.get("extra") or {}
    metadata = extra.get("metadata") or {}
    semgrep_severity = str(extra.get("severity") or metadata.get("impact") or "medium").lower()
    severity = {"error": "high", "warning": "medium"}.get(semgrep_severity, normalize_severity(semgrep_severity))
    path = row.get("path") or "unknown"
    start = (row.get("start") or {}).get("line")
    location = f"{path}:{start}" if start else path
    return {
        "id": f"semgrep-{row.get('check_id', 'rule')}",
        "title": extra.get("message") or row.get("check_id") or "Semgrep finding",
        "severity": severity,
        "cwe_id": (metadata.get("cwe") or [None])[0] if isinstance(metadata.get("cwe"), list) else metadata.get("cwe"),
        "location": location,
        "parameter": None,
        "payload": None,
        "evidence": extra.get("lines"),
        "confidence": 82,
        "summary": extra.get("message") or "Semgrep static analysis finding.",
        "reproduction_steps": [
            f"Run semgrep scan --config auto --json --quiet {repo_path}.",
            f"Inspect {location}.",
        ],
        "source": "semgrep",
        "raw": row,
    }


def _normalize_bandit(row: dict[str, Any], repo_path: Path) -> dict[str, Any]:
    severity = normalize_severity(row.get("issue_severity"))
    location = f"{row.get('filename', 'unknown')}:{row.get('line_number', '')}".rstrip(":")
    return {
        "id": f"bandit-{row.get('test_id', 'test')}-{row.get('line_number', '0')}",
        "title": row.get("test_name") or "Bandit finding",
        "severity": severity,
        "cwe_id": None,
        "location": location,
        "parameter": None,
        "payload": None,
        "evidence": row.get("code"),
        "confidence": 80,
        "summary": row.get("issue_text") or "Bandit Python SAST finding.",
        "reproduction_steps": [
            f"Run bandit -r {repo_path} -f json.",
            f"Inspect {location}.",
        ],
        "source": "bandit",
        "raw": row,
    }


async def run_semgrep_scan(
    target: str,
    *,
    intent_plan: dict[str, Any] | None,
    token: str | None,
) -> EngineResult:
    return await _run_sast_scan(target, engine="semgrep", intent_plan=intent_plan, token=token)


async def run_bandit_scan(
    target: str,
    *,
    intent_plan: dict[str, Any] | None,
    token: str | None,
) -> EngineResult:
    return await _run_sast_scan(target, engine="bandit", intent_plan=intent_plan, token=token)


async def _run_sast_scan(
    target: str,
    *,
    engine: str,
    intent_plan: dict[str, Any] | None,
    token: str | None,
) -> EngineResult:
    result = EngineResult(engine=engine, available=False)
    decision = evaluate_agent_action(
        intent_plan=intent_plan,
        token=token,
        action=f"scanner.{engine}",
    )
    result.policy_decisions.append(decision.as_dict())
    if not decision.allowed:
        result.errors.append(decision.reason)
        result.observations.append({"engine": engine, "blocked_by_policy": decision.reason})
        return result

    repo_path = resolve_local_repo(target)
    if repo_path is None:
        result.errors.append("No local repository path is available for SAST scan")
        result.observations.append(
            {
                "engine": engine,
                "available": False,
                "message": "Provide a local repository path or checked-out file:// target for SAST scanning.",
            }
        )
        return result

    binary = shutil.which(engine)
    if not binary:
        result.findings.extend(_static_fallback(repo_path, engine=engine))
        result.errors.append(f"{engine} CLI is not installed or not on PATH; used fallback static rules")
        result.observations.append(
            {
                "engine": engine,
                "available": False,
                "fallback": True,
                "repo_path": str(repo_path),
                "findings": len(result.findings),
            }
        )
        return result

    result.available = True
    try:
        if engine == "semgrep":
            code, stdout, stderr = await run_json_command(
                [binary, "scan", "--config", "auto", "--json", "--quiet", str(repo_path)],
                timeout_seconds=180,
            )
            data = json.loads(stdout or "{}")
            rows = data.get("results", [])
            result.findings.extend(_normalize_semgrep(row, repo_path) for row in rows)
        else:
            code, stdout, stderr = await run_json_command(
                [binary, "-r", str(repo_path), "-f", "json"],
                timeout_seconds=180,
            )
            data = json.loads(stdout or "{}")
            rows = data.get("results", [])
            result.findings.extend(_normalize_bandit(row, repo_path) for row in rows)
        result.observations.append(
            {
                "engine": engine,
                "available": True,
                "return_code": code,
                "repo_path": str(repo_path),
                "findings": len(result.findings),
            }
        )
        if stderr.strip():
            result.errors.append(stderr.strip()[:1000])
    except TimeoutError:
        result.errors.append(f"{engine} scan timed out")
    except Exception as exc:
        result.errors.append(str(exc))
    return result
