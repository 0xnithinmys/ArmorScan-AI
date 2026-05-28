from __future__ import annotations

import shutil
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class ScannerCapability:
    name: str
    category: str
    scan_types: list[str]
    passive: bool
    safe_active: bool
    auth_aware: bool
    output_format: str
    installed: bool
    command: str | None
    notes: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


SCANNER_REGISTRY = [
    ScannerCapability(
        name="nuclei",
        category="web-template-scanner",
        scan_types=["url", "api"],
        passive=False,
        safe_active=True,
        auth_aware=False,
        output_format="jsonl",
        installed=False,
        command="nuclei",
        notes="Template-driven HTTP checks under signed scope policy.",
    ),
    ScannerCapability(
        name="zap-baseline",
        category="web-passive-dast",
        scan_types=["url", "api"],
        passive=True,
        safe_active=False,
        auth_aware=False,
        output_format="json",
        installed=False,
        command="zap-baseline.py",
        notes="OWASP ZAP baseline/passive scan. Session-aware active contexts are planned separately.",
    ),
    ScannerCapability(
        name="semgrep",
        category="sast",
        scan_types=["github"],
        passive=True,
        safe_active=False,
        auth_aware=False,
        output_format="json",
        installed=False,
        command="semgrep",
        notes="Static source scanning with rule metadata.",
    ),
    ScannerCapability(
        name="bandit",
        category="python-sast",
        scan_types=["github"],
        passive=True,
        safe_active=False,
        auth_aware=False,
        output_format="json",
        installed=False,
        command="bandit",
        notes="Python security linting.",
    ),
    ScannerCapability(
        name="gitleaks",
        category="secret-scanning",
        scan_types=["github"],
        passive=True,
        safe_active=False,
        auth_aware=False,
        output_format="json",
        installed=False,
        command="gitleaks",
        notes="Secret detection. Validation of discovered secrets stays out of scope by default.",
    ),
    ScannerCapability(
        name="trivy",
        category="supply-chain",
        scan_types=["github"],
        passive=True,
        safe_active=False,
        auth_aware=False,
        output_format="json",
        installed=False,
        command="trivy",
        notes="Dependency, filesystem, container, and IaC scanning.",
    ),
]


def scanner_capabilities_for(scan_type: str) -> list[dict[str, Any]]:
    capabilities: list[dict[str, Any]] = []
    for capability in SCANNER_REGISTRY:
        if scan_type not in capability.scan_types:
            continue
        item = capability.as_dict()
        command = item.get("command")
        item["installed"] = bool(command and shutil.which(command))
        capabilities.append(item)
    return capabilities


def normalize_engine_record(record: dict[str, Any], *, default_source: str) -> dict[str, Any]:
    evidence = record.get("evidence") or record.get("description") or record.get("summary")
    return {
        "source": record.get("source") or record.get("engine") or default_source,
        "title": record.get("title") or record.get("name") or "Scanner observation",
        "location": record.get("location") or record.get("url") or record.get("path") or "unknown",
        "severity": str(record.get("severity") or "info").lower(),
        "confidence": record.get("confidence", 70),
        "evidence": evidence,
        "raw": record,
    }
