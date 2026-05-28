from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from armorscan.tools.engine_common import ensure_repo_target


DEPENDENCY_FILES = {
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
}

IAC_FILES = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".github/workflows",
    "terraform.tf",
    "main.tf",
    "deployment.yaml",
    "service.yaml",
    "kustomization.yaml",
}


async def inspect_supply_chain(target: str) -> dict[str, Any]:
    repo_path, errors, repo_meta = await ensure_repo_target(target)
    if repo_path is None:
        return {
            "dependency_inventory": [],
            "iac_inventory": [],
            "repo_inventory": [{"repo_meta": repo_meta}],
            "errors": errors,
        }

    dependencies: list[dict[str, Any]] = []
    iac: list[dict[str, Any]] = []
    repo_inventory: list[dict[str, Any]] = []
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", "node_modules", ".venv", "__pycache__"} for part in path.parts):
            continue
        rel = str(path.relative_to(repo_path))
        if path.name in DEPENDENCY_FILES:
            dependencies.append(_summarize_dependency_file(path, repo_path))
        if path.name in IAC_FILES or any(marker in rel for marker in [".github/workflows", "k8s", "kubernetes"]):
            iac.append(_summarize_iac_file(path, repo_path))
        if path.suffix.lower() in {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rs"}:
            repo_inventory.append({"path": rel, "kind": "source", "language": _language_for(path)})

    return {
        "dependency_inventory": dependencies[:100],
        "iac_inventory": iac[:100],
        "repo_inventory": repo_inventory[:500],
        "errors": [],
    }


def _summarize_dependency_file(path: Path, repo_path: Path) -> dict[str, Any]:
    rel = str(path.relative_to(repo_path))
    item: dict[str, Any] = {"path": rel, "kind": "dependency-manifest", "package_count": None}
    if path.name == "package.json":
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            data = {}
        deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
        item["package_count"] = len(deps)
        item["packages"] = sorted(deps)[:50]
    elif path.name == "requirements.txt":
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        item["package_count"] = len(lines)
        item["packages"] = lines[:50]
    return item


def _summarize_iac_file(path: Path, repo_path: Path) -> dict[str, Any]:
    rel = str(path.relative_to(repo_path))
    text = path.read_text(encoding="utf-8", errors="ignore")[:5000].lower()
    signals = []
    for marker in ["privileged", "hostnetwork", "latest", "0.0.0.0", "password", "secret", "root"]:
        if marker in text:
            signals.append(marker)
    return {"path": rel, "kind": "iac-or-deployment", "signals": signals}


def _language_for(path: Path) -> str:
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".java": "java",
        ".rs": "rust",
    }.get(path.suffix.lower(), "unknown")
