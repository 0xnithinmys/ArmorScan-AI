from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from armorscan.policy import evaluate_agent_action
from armorscan.utils import normalize_target_url


OPENAPI_CANDIDATES = [
    "/openapi.json",
    "/swagger.json",
    "/api-docs",
    "/v3/api-docs",
    "/docs",
    "/swagger/v1/swagger.json",
]


def _same_host(base_url: str, candidate: str) -> bool:
    base = urlparse(normalize_target_url(base_url))
    parsed = urlparse(candidate if "://" in candidate else urljoin(normalize_target_url(base_url), candidate))
    return bool(base.hostname and parsed.hostname == base.hostname)


def extract_js_endpoints(text: str, *, base_url: str, source: str) -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []
    patterns = [
        r"""fetch\(["']([^"']+)["']""",
        r"""axios\.(?:get|post|put|patch|delete)\(["']([^"']+)["']""",
        r"""(?:url|endpoint|path)\s*[:=]\s*["'](/[^"']{2,160})["']""",
        r"""["']((?:/api|/graphql|/v[0-9]/)[^"']{0,160})["']""",
    ]
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            raw = match.group(1).strip()
            if not raw or raw.startswith(("data:", "mailto:", "tel:")):
                continue
            endpoint = urljoin(normalize_target_url(base_url), raw)
            if not _same_host(base_url, endpoint) or endpoint in seen:
                continue
            seen.add(endpoint)
            endpoints.append({"url": endpoint, "source": source, "raw": raw})
    return endpoints


async def discover_api_surface(
    target_url: str,
    *,
    routes: list[str],
    browser_observations: list[dict[str, Any]],
    http_observations: list[dict[str, Any]],
    intent_plan: dict[str, Any] | None,
    token: str | None,
) -> dict[str, Any]:
    target_url = normalize_target_url(target_url)
    discovered: list[dict[str, Any]] = []
    js_endpoints: list[dict[str, Any]] = []
    errors: list[str] = []
    policy_decisions: list[dict[str, Any]] = []
    candidate_urls = [urljoin(target_url.rstrip("/") + "/", item.lstrip("/")) for item in OPENAPI_CANDIDATES]

    for observation in browser_observations:
        for request in observation.get("requests", []):
            url = str(request.get("url") or "")
            resource_type = request.get("resource_type")
            if not _same_host(target_url, url):
                continue
            if "/api" in url or "/graphql" in url or resource_type in {"xhr", "fetch"}:
                discovered.append(
                    {
                        "url": url,
                        "method": request.get("method") or "GET",
                        "source": "browser-network",
                        "kind": "network-api",
                    }
                )
            if resource_type == "script":
                candidate_urls.append(url)

    for route in routes:
        if any(marker in route.lower() for marker in ["/api", "/graphql", "swagger", "openapi"]):
            discovered.append({"url": route, "method": "GET", "source": "route-inference", "kind": "api-route"})

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for candidate in list(dict.fromkeys(candidate_urls))[:25]:
            decision = evaluate_agent_action(
                intent_plan=intent_plan,
                token=token,
                action="http.get",
                url=candidate,
            )
            policy_decisions.append(decision.as_dict())
            if not decision.allowed:
                continue
            try:
                response = await client.get(candidate)
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")
                continue
            content_type = response.headers.get("content-type", "")
            text = response.text[:200000]
            if response.status_code >= 400:
                continue
            if candidate.endswith(".js") or "javascript" in content_type:
                js_endpoints.extend(extract_js_endpoints(text, base_url=target_url, source=candidate))
                continue
            parsed_spec = _parse_api_spec(text, source=candidate)
            if parsed_spec:
                discovered.extend(parsed_spec)

    for observation in http_observations:
        text = str(observation.get("body_excerpt") or "")
        js_endpoints.extend(extract_js_endpoints(text, base_url=target_url, source=str(observation.get("url"))))

    for endpoint in js_endpoints:
        discovered.append(
            {"url": endpoint["url"], "method": "UNKNOWN", "source": endpoint["source"], "kind": "js-endpoint"}
        )

    return {
        "discovered_apis": _dedupe_api(discovered),
        "discovered_js_endpoints": _dedupe_api(js_endpoints),
        "errors": errors,
        "policy_decisions": policy_decisions,
    }


def _parse_api_spec(text: str, *, source: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    paths = data.get("paths")
    if not isinstance(paths, dict):
        return []
    endpoints: list[dict[str, Any]] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods:
            if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue
            endpoints.append(
                {
                    "url": path,
                    "method": method.upper(),
                    "source": source,
                    "kind": "openapi",
                }
            )
    return endpoints


def _dedupe_api(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        key = (str(item.get("method") or ""), str(item.get("url") or ""))
        if key in seen or not key[1]:
            continue
        seen.add(key)
        output.append(item)
    return output[:200]
