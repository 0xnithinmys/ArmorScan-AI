from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from armorscan.tools.engine_common import ensure_repo_target


MANIFEST_FILES = [
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "poetry.lock",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "pom.xml",
    "go.mod",
]

ROUTE_PATTERNS = [
    re.compile(r"""@(?:app|router)\.(get|post|put|delete|patch)\(["']([^"']+)["']"""),
    re.compile(r"""router\.(get|post|put|delete|patch)\(["']([^"']+)["']"""),
    re.compile(r"""app\.(get|post|put|delete|patch)\(["']([^"']+)["']"""),
]


async def inspect_repository(target: str) -> dict[str, Any]:
    repo_path, errors, repo_meta = await ensure_repo_target(target)
    if repo_path is None:
        return {
            "repo_path": None,
            "errors": errors,
            "policy_decisions": [],
            "frameworks": [],
            "languages": [],
            "routes": [],
            "inputs": [],
            "observations": [{"repo_meta": repo_meta}],
        }

    manifests = [name for name in MANIFEST_FILES if (repo_path / name).exists()]
    routes: list[str] = []
    inputs: list[dict[str, Any]] = []
    frameworks: set[str] = set()
    languages: set[str] = set()

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue
        if any(part in {".git", "node_modules", ".venv", "__pycache__"} for part in file_path.parts):
            continue
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            languages.add("python")
        elif suffix in {".js", ".jsx"}:
            languages.add("javascript")
        elif suffix in {".ts", ".tsx"}:
            languages.add("typescript")

        if file_path.name == "package.json":
            try:
                package_json = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
            except json.JSONDecodeError:
                package_json = {}
            deps = {**(package_json.get("dependencies") or {}), **(package_json.get("devDependencies") or {})}
            for dep in deps:
                dep_lower = dep.lower()
                if dep_lower in {"next", "react", "express", "nestjs", "fastify"}:
                    frameworks.add(dep_lower)
        if file_path.name == "requirements.txt":
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for pkg in ["django", "fastapi", "flask"]:
                if pkg in text:
                    frameworks.add(pkg)

        if suffix not in {".py", ".js", ".jsx", ".ts", ".tsx"}:
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        if "graphql" in lower:
            frameworks.add("graphql")
        if "openapi" in lower or "swagger" in lower:
            frameworks.add("openapi")
        for pattern in ROUTE_PATTERNS:
            for match in pattern.finditer(text):
                routes.append(match.group(2))
        for name in re.findall(r"""(?:name|id|param)\s*[:=]\s*["']([A-Za-z0-9_.-]{2,60})["']""", text):
            if len(inputs) >= 50:
                break
            inputs.append({"name": name, "source_file": str(file_path.relative_to(repo_path))})

    return {
        "repo_path": str(repo_path),
        "errors": [],
        "policy_decisions": [],
        "frameworks": sorted(frameworks),
        "languages": sorted(languages),
        "routes": sorted(dict.fromkeys(routes))[:100],
        "inputs": inputs[:50],
        "observations": [
            {
                "repo_meta": repo_meta,
                "manifests": manifests,
                "languages": sorted(languages),
                "frameworks": sorted(frameworks),
                "routes": len(routes),
                "inputs": len(inputs),
            }
        ],
    }
