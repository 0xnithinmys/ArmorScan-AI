from __future__ import annotations

import json
import re
import ast
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
    "openapi.json",
    "swagger.json",
    "postman_collection.json",
    "nginx.conf",
    "terraform.tf",
]

ROUTE_PATTERNS = [
    re.compile(r"""@(?:app|router)\.(get|post|put|delete|patch)\(["']([^"']+)["']"""),
    re.compile(r"""router\.(get|post|put|delete|patch)\(["']([^"']+)["']"""),
    re.compile(r"""app\.(get|post|put|delete|patch)\(["']([^"']+)["']"""),
    re.compile(r"""(?:route|path)\s*[:=]\s*["'](/[^"']{1,160})["']"""),
    re.compile(r"""export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE)\s*\("""),
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
    route_details: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    api_specs: list[dict[str, Any]] = []
    iac_files: list[dict[str, Any]] = []
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
            if (repo_path / "app").exists() or (repo_path / "pages").exists():
                frameworks.add("next")
        if file_path.name == "requirements.txt":
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for pkg in ["django", "fastapi", "flask"]:
                if pkg in text:
                    frameworks.add(pkg)
        if file_path.name in {"openapi.json", "swagger.json"}:
            api_specs.extend(_parse_openapi_file(file_path, repo_path))
        if "postman" in file_path.name.lower() and file_path.suffix.lower() == ".json":
            api_specs.extend(_parse_postman_file(file_path, repo_path))
        if file_path.name in {"Dockerfile", "docker-compose.yml", "docker-compose.yaml"} or file_path.suffix.lower() in {
            ".tf",
            ".yaml",
            ".yml",
        }:
            iac_files.append(_summarize_iac(file_path, repo_path))

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
        if "router" in lower or "route" in lower or "fastapi" in lower:
            for route in _extract_python_ast_routes(text, file_path, repo_path):
                routes.append(route["path"])
                route_details.append(route)
        if file_path.name in {"route.ts", "route.js"}:
            app_route = _next_app_route(file_path, repo_path)
            if app_route:
                routes.append(app_route)
                route_details.append({"path": app_route, "method": "UNKNOWN", "source_file": str(file_path.relative_to(repo_path)), "framework": "next"})
        for pattern in ROUTE_PATTERNS:
            for match in pattern.finditer(text):
                if len(match.groups()) >= 2:
                    method, route = match.group(1), match.group(2)
                    routes.append(route)
                    route_details.append(
                        {
                            "path": route,
                            "method": method.upper(),
                            "source_file": str(file_path.relative_to(repo_path)),
                            "framework": "regex",
                        }
                    )
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
                "route_details": route_details[:100],
                "api_specs": api_specs[:100],
                "iac_files": iac_files[:100],
            }
        ],
    }


def _extract_python_ast_routes(text: str, file_path: Path, repo_path: Path) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return routes
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        method = func.attr.lower()
        if method not in {"get", "post", "put", "patch", "delete"}:
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
            continue
        routes.append(
            {
                "path": node.args[0].value,
                "method": method.upper(),
                "source_file": str(file_path.relative_to(repo_path)),
                "framework": "python-ast",
            }
        )
    return routes


def _next_app_route(file_path: Path, repo_path: Path) -> str | None:
    try:
        rel = file_path.relative_to(repo_path)
    except ValueError:
        return None
    parts = list(rel.parts)
    if "app" not in parts:
        return None
    app_index = parts.index("app")
    route_parts = parts[app_index + 1 : -1]
    clean_parts = [part for part in route_parts if not part.startswith("(")]
    if not clean_parts:
        return "/"
    return "/" + "/".join(part.replace("[", "{").replace("]", "}") for part in clean_parts)


def _parse_openapi_file(file_path: Path, repo_path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return []
    paths = data.get("paths") if isinstance(data, dict) else None
    if not isinstance(paths, dict):
        return []
    endpoints = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods:
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                endpoints.append(
                    {
                        "path": path,
                        "method": method.upper(),
                        "source_file": str(file_path.relative_to(repo_path)),
                        "framework": "openapi",
                    }
                )
    return endpoints


def _parse_postman_file(file_path: Path, repo_path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return []
    endpoints: list[dict[str, Any]] = []
    stack = list(data.get("item", [])) if isinstance(data, dict) else []
    while stack:
        item = stack.pop()
        if not isinstance(item, dict):
            continue
        stack.extend(item.get("item", []) or [])
        request = item.get("request")
        if not isinstance(request, dict):
            continue
        url = request.get("url")
        raw = url.get("raw") if isinstance(url, dict) else url
        if raw:
            endpoints.append(
                {
                    "path": str(raw),
                    "method": str(request.get("method") or "GET").upper(),
                    "source_file": str(file_path.relative_to(repo_path)),
                    "framework": "postman",
                }
            )
    return endpoints


def _summarize_iac(file_path: Path, repo_path: Path) -> dict[str, Any]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")[:5000].lower()
    signals = [marker for marker in ["privileged", "latest", "0.0.0.0", "secret", "password", "root"] if marker in text]
    return {"path": str(file_path.relative_to(repo_path)), "signals": signals}
