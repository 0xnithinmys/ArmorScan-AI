from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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


async def run_json_command(args: list[str], *, timeout_seconds: int = 90) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")


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
