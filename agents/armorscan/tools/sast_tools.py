from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from armorscan.policy import evaluate_agent_action
from armorscan.tools.engine_common import EngineResult, ensure_repo_target, normalize_severity, run_json_command


STATIC_PATTERNS = [
    (
        "python-shell-true",
        {".py"},
        re.compile(r"shell\s*=\s*True"),
        "high",
        "CWE-78",
        "Python subprocess uses shell=True",
    ),
    (
        "python-eval",
        {".py"},
        re.compile(r"\beval\s*\("),
        "high",
        "CWE-95",
        "Python eval() executes dynamic code",
    ),
    (
        "python-exec",
        {".py"},
        re.compile(r"\bexec\s*\("),
        "high",
        "CWE-95",
        "Python exec() executes dynamic code",
    ),
    (
        "python-pickle",
        {".py"},
        re.compile(r"pickle\.loads?\s*\("),
        "medium",
        "CWE-502",
        "Pickle deserialization detected",
    ),
    (
        "python-yaml-load",
        {".py"},
        re.compile(r"yaml\.load\s*\("),
        "medium",
        "CWE-502",
        "yaml.load() may deserialize unsafe data",
    ),
    (
        "tls-verify-false",
        {".py", ".js", ".jsx", ".ts", ".tsx"},
        re.compile(r"verify\s*=\s*False"),
        "medium",
        "CWE-295",
        "TLS certificate verification disabled",
    ),
    (
        "js-eval",
        {".js", ".jsx", ".ts", ".tsx"},
        re.compile(r"\beval\s*\("),
        "high",
        "CWE-95",
        "JavaScript eval() executes dynamic code",
    ),
    (
        "js-inner-html",
        {".js", ".jsx", ".ts", ".tsx"},
        re.compile(r"(innerHTML\s*=|dangerouslySetInnerHTML)"),
        "medium",
        "CWE-79",
        "Raw HTML injection sink detected",
    ),
    (
        "hardcoded-secret",
        {".py", ".js", ".jsx", ".ts", ".tsx"},
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"),
        "medium",
        "CWE-798",
        "Possible hardcoded secret",
    ),
]
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _github_blob_location(target: str, rel: Path | str, line: int | str | None = None) -> str:
    parsed = urlparse(target)
    if parsed.netloc.lower() != "github.com":
        suffix = f":{line}" if line else ""
        return f"{rel}{suffix}"
    repo_path = parsed.path.strip("/").removesuffix(".git")
    if repo_path.count("/") < 1:
        suffix = f":{line}" if line else ""
        return f"{rel}{suffix}"
    rel_path = str(rel).replace("\\", "/")
    location = f"https://github.com/{repo_path}/blob/main/{rel_path}"
    return f"{location}#L{line}" if line else location


def _static_fallback(repo_path: Path, *, engine: str, target: str) -> list[dict[str, Any]]:
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
        for pattern_id, extensions, pattern, severity, cwe_id, title in STATIC_PATTERNS:
            if file_path.suffix.lower() not in extensions:
                continue
            for match in pattern.finditer(text):
                line = _line_for_offset(text, match.start())
                rel = file_path.relative_to(repo_path)
                findings.append(
                    {
                        "id": f"{engine}-fallback-{pattern_id}-{len(findings) + 1}",
                        "title": title,
                        "severity": severity,
                        "cwe_id": cwe_id,
                        "location": _github_blob_location(target, rel, line),
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


def _normalize_semgrep(row: dict[str, Any], repo_path: Path, target: str) -> dict[str, Any]:
    extra = row.get("extra") or {}
    metadata = extra.get("metadata") or {}
    semgrep_severity = str(extra.get("severity") or metadata.get("impact") or "medium").lower()
    severity = {"error": "high", "warning": "medium"}.get(semgrep_severity, normalize_severity(semgrep_severity))
    path = row.get("path") or "unknown"
    start = (row.get("start") or {}).get("line")
    location = _github_blob_location(target, path, start)
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


def _normalize_bandit(row: dict[str, Any], repo_path: Path, target: str) -> dict[str, Any]:
    severity = normalize_severity(row.get("issue_severity"))
    raw_path = Path(str(row.get("filename") or "unknown"))
    try:
        rel_path = raw_path.relative_to(repo_path)
    except ValueError:
        rel_path = raw_path
    location = _github_blob_location(target, rel_path, row.get("line_number"))
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


def _normalize_gitleaks(row: dict[str, Any], repo_path: Path, target: str) -> dict[str, Any]:
    rel = row.get("File") or row.get("file") or "unknown"
    line = row.get("StartLine") or row.get("start_line")
    location = _github_blob_location(target, rel, line)
    secret_type = row.get("RuleID") or row.get("Description") or "Potential secret"
    return {
        "id": f"gitleaks-{secret_type}-{line or 0}",
        "title": f"Potential secret exposure: {secret_type}",
        "severity": "high",
        "cwe_id": "CWE-798",
        "location": location,
        "parameter": None,
        "payload": None,
        "evidence": (row.get("Match") or row.get("Secret") or "")[:200],
        "confidence": 88,
        "summary": row.get("Description") or "Potential credential or token material was detected in repository contents.",
        "reproduction_steps": [
            f"Open {location}.",
            "Verify whether the value is a live secret, test fixture, or false positive.",
        ],
        "source": "gitleaks",
        "raw": row,
    }


def _normalize_trivy_result(row: dict[str, Any], repo_path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    target = row.get("Target") or str(repo_path)
    for vuln in row.get("Vulnerabilities") or []:
        findings.append(
            {
                "id": f"trivy-{vuln.get('VulnerabilityID', 'issue')}",
                "title": vuln.get("Title") or vuln.get("PkgName") or "Dependency vulnerability",
                "severity": normalize_severity(vuln.get("Severity")),
                "cwe_id": None,
                "location": target,
                "parameter": vuln.get("PkgName"),
                "payload": None,
                "evidence": vuln.get("InstalledVersion"),
                "confidence": 84,
                "summary": vuln.get("Description") or "Trivy detected a vulnerable dependency or config issue.",
                "reproduction_steps": [
                    f"Run trivy fs --scanners vuln,secret,misconfig --format json {repo_path}.",
                    f"Review package {vuln.get('PkgName')} in {target}.",
                ],
                "source": "trivy",
                "raw": vuln,
            }
        )
    for misconfig in row.get("Misconfigurations") or []:
        findings.append(
            {
                "id": f"trivy-misconfig-{misconfig.get('ID', 'issue')}",
                "title": misconfig.get("Title") or misconfig.get("Message") or "Configuration issue",
                "severity": normalize_severity(misconfig.get("Severity")),
                "cwe_id": None,
                "location": target,
                "parameter": misconfig.get("Type"),
                "payload": None,
                "evidence": misconfig.get("Resolution"),
                "confidence": 80,
                "summary": misconfig.get("Description") or "Trivy detected a configuration weakness.",
                "reproduction_steps": [
                    f"Run trivy fs --scanners vuln,secret,misconfig --format json {repo_path}.",
                    f"Review the configuration finding in {target}.",
                ],
                "source": "trivy",
                "raw": misconfig,
            }
        )
    return findings


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


async def run_gitleaks_scan(
    target: str,
    *,
    intent_plan: dict[str, Any] | None,
    token: str | None,
) -> EngineResult:
    return await _run_sast_scan(target, engine="gitleaks", intent_plan=intent_plan, token=token)


async def run_trivy_scan(
    target: str,
    *,
    intent_plan: dict[str, Any] | None,
    token: str | None,
) -> EngineResult:
    return await _run_sast_scan(target, engine="trivy", intent_plan=intent_plan, token=token)


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

    repo_path, repo_errors, repo_meta = await ensure_repo_target(target)
    if repo_path is None:
        result.errors.extend(repo_errors or ["No local repository path is available for SAST scan"])
        result.observations.append(
            {
                "engine": engine,
                "available": False,
                "message": "Provide a local repository path or an accessible GitHub repository URL for SAST scanning.",
                "repo_meta": repo_meta,
            }
        )
        return result

    binary = shutil.which(engine)
    if not binary:
        if engine in {"semgrep", "bandit"}:
            result.findings.extend(_static_fallback(repo_path, engine=engine, target=target))
            result.errors.append(f"{engine} CLI is not installed or not on PATH; used fallback static rules")
        else:
            result.errors.append(f"{engine} CLI is not installed or not on PATH")
        result.observations.append(
            {
                "engine": engine,
                "available": False,
                "fallback": engine in {"semgrep", "bandit"},
                "repo_path": str(repo_path),
                "findings": len(result.findings),
                "repo_meta": repo_meta,
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
            result.findings.extend(_normalize_semgrep(row, repo_path, target) for row in rows)
        elif engine == "bandit":
            code, stdout, stderr = await run_json_command(
                [binary, "-r", str(repo_path), "-f", "json"],
                timeout_seconds=180,
            )
            data = json.loads(stdout or "{}")
            rows = data.get("results", [])
            result.findings.extend(_normalize_bandit(row, repo_path, target) for row in rows)
        elif engine == "gitleaks":
            code, stdout, stderr = await run_json_command(
                [binary, "detect", "--no-git", "--source", str(repo_path), "--report-format", "json", "--report-path", "-"],
                timeout_seconds=180,
            )
            rows = json.loads(stdout or "[]")
            if isinstance(rows, list):
                result.findings.extend(_normalize_gitleaks(row, repo_path, target) for row in rows)
        else:
            code, stdout, stderr = await run_json_command(
                [binary, "fs", "--scanners", "vuln,secret,misconfig", "--format", "json", str(repo_path)],
                timeout_seconds=240,
            )
            data = json.loads(stdout or "{}")
            for row in data.get("Results") or []:
                result.findings.extend(_normalize_trivy_result(row, repo_path))
        result.observations.append(
            {
                "engine": engine,
                "available": True,
                "return_code": code,
                "repo_path": str(repo_path),
                "findings": len(result.findings),
                "repo_meta": repo_meta,
            }
        )
        if stderr.strip():
            result.errors.append(stderr.strip()[:1000])
    except TimeoutError:
        result.errors.append(f"{engine} scan timed out")
    except Exception as exc:
        result.errors.append(str(exc))
    return result
