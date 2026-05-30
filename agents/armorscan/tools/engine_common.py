from __future__ import annotations

import asyncio
import json
import subprocess
import shutil
import tempfile
from hashlib import sha256
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass(slots=True)
class EngineResult:
    engine: str
    available: bool
    findings: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    policy_decisions: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "available": self.available,
            "findings": self.findings,
            "observations": self.observations,
            "errors": self.errors,
            "policy_decisions": self.policy_decisions,
        }


def normalize_severity(value: str | None) -> str:
    severity = (value or "info").lower()
    return severity if severity in SEVERITY_ORDER else "info"


def resolve_local_repo(target: str) -> Path | None:
    candidate = Path(target).expanduser()
    if candidate.exists():
        return candidate.resolve()
    if target.startswith("file://"):
        file_candidate = Path(target.removeprefix("file://")).expanduser()
        if file_candidate.exists():
            return file_candidate.resolve()
    return None


def is_remote_repo_target(target: str) -> bool:
    value = target.strip().lower()
    return value.startswith(("http://", "https://", "git@")) and "github.com" in value


def _clone_root() -> Path:
    root = Path(tempfile.gettempdir()) / "armorscan-repos"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _repo_dirname(target: str) -> str:
    parsed = urlparse(target if "://" in target else f"https://{target}")
    stem = Path(parsed.path.rstrip("/")).stem or "repo"
    suffix = sha256(target.encode("utf-8")).hexdigest()[:10]
    return f"{stem}-{suffix}"


async def ensure_repo_target(target: str) -> tuple[Path | None, list[str], dict[str, Any]]:
    local = resolve_local_repo(target)
    if local is not None:
        return local, [], {"mode": "local", "path": str(local)}

    if not is_remote_repo_target(target):
        return None, ["No local repository path is available for SAST scan"], {"mode": "unresolved"}

    git_binary = shutil.which("git")
    if not git_binary:
        return None, ["git is not installed or not on PATH for remote repository cloning"], {"mode": "remote"}

    clone_dir = _clone_root() / _repo_dirname(target)
    if clone_dir.exists():
        return clone_dir.resolve(), [], {"mode": "remote-cache", "path": str(clone_dir.resolve())}

    args = [git_binary, "clone", "--depth", "1", target, str(clone_dir)]
    return_code, stdout, stderr = await run_json_command(args, timeout_seconds=240)
    if return_code != 0 or not clone_dir.exists():
        detail = stderr.strip() or stdout.strip() or "git clone failed"
        return None, [detail[:1000]], {"mode": "remote-failed", "target": target}
    return clone_dir.resolve(), [], {"mode": "remote-clone", "path": str(clone_dir.resolve())}


async def run_json_command(args: list[str], *, timeout_seconds: int = 90) -> tuple[int, str, str]:
    def _run() -> tuple[int, str, str]:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return completed.returncode, completed.stdout, completed.stderr

    return await asyncio.to_thread(_run)


def parse_json_lines(output: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows
