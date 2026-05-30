from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from armorscan.llm import GroqResponsesClient
from armorscan.policy import evaluate_agent_action
from armorscan.state import FindingDraft, ScanState
from armorscan.tools.playwright_tools import run_browser_recon
from armorscan.tools.repo_tools import inspect_repository
from armorscan.utils import normalize_target_url

COMMON_PATHS = ["/", "/login", "/search", "/api", "/health", "/graphql"]


def _host_label(target_url: str) -> str:
    parsed = urlparse(normalize_target_url(target_url))
    return parsed.netloc or parsed.path


def _route_is_present(routes: list[str], suffix: str) -> bool:
    normalized_suffix = suffix.rstrip("/").lower()
    for route in routes:
        route_value = str(route).rstrip("/").lower()
        if route_value.endswith(normalized_suffix):
            return True
    return False


def _looks_like_search_control(item: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(item.get(key) or "")
        for key in ("type", "name", "id", "placeholder", "aria_label", "autocomplete", "role")
    ).lower()
    return any(marker in haystack for marker in ("search", "query", "filter", "find"))


def _looks_like_password_control(item: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(item.get(key) or "")
        for key in ("type", "name", "id", "placeholder", "aria_label", "autocomplete", "role", "purpose")
    ).lower()
    return any(marker in haystack for marker in ("password", "passcode", "secret"))


def _has_search_surface(state: ScanState) -> bool:
    if any(_looks_like_search_control(item) for item in state.get("discovered_inputs", [])):
        return True
    for form in state.get("discovered_forms", []):
        form_text = " ".join(str(form.get(key) or "") for key in ("action", "method", "input_count"))
        if any(marker in form_text.lower() for marker in ("search", "query", "filter", "find")):
            return True
    for observation in state.get("browser_observations", []):
        for control in observation.get("clickable_surfaces", []):
            control_text = " ".join(
                str(control.get(key) or "") for key in ("text", "tag", "kind", "reason")
            ).lower()
            if any(marker in control_text for marker in ("search", "query", "filter", "find")):
                return True
    return False


def _has_password_surface(state: ScanState) -> bool:
    return any(_looks_like_password_control(item) for item in state.get("discovered_inputs", []))


def draft_has_evidence(draft: dict[str, Any], state: ScanState) -> bool:
    title = str(draft.get("title") or "").lower()
    url = str(draft.get("url") or "").lower()
    parameter = str(draft.get("parameter") or "").lower()
    routes = state.get("discovered_routes", [])

    if "admin" in title or "/admin" in url or url.rstrip("/").endswith("admin"):
        return _route_is_present(routes, "/admin")
    if "search" in title or parameter in {"q", "query", "search"} or "/search" in url:
        return _has_search_surface(state)
    if "graphql" in title or "/graphql" in url:
        return _route_is_present(routes, "/graphql") or any(
            "graphql" in str(item).lower() for item in state.get("discovered_apis", [])
        )
    if "api" in title or "/api" in url:
        return bool(state.get("discovered_apis")) or _route_is_present(routes, "/api")
    if any(marker in title for marker in ("auth", "login", "signin")):
        return _has_password_surface(state) or _route_is_present(routes, "/login")
    return True


async def passive_recon(
    target_url: str,
    *,
    scan_type: str = "url",
    intent_plan: dict[str, Any] | None,
    token: str | None,
) -> dict[str, Any]:
    if scan_type == "github":
        repo_recon = await inspect_repository(target_url)
        return {
            "discovered_routes": repo_recon["routes"],
            "discovered_forms": [],
            "discovered_inputs": repo_recon["inputs"][:20],
            "browser_observations": repo_recon["observations"],
            "browser_errors": repo_recon["errors"],
            "policy_decisions": repo_recon.get("policy_decisions", []),
            "technology_stack": list(dict.fromkeys(repo_recon["frameworks"] + repo_recon["languages"])),
            "http_observations": [{"repo_path": repo_recon["repo_path"], "frameworks": repo_recon["frameworks"]}],
        }

    target_url = normalize_target_url(target_url)
    observations: list[dict[str, Any]] = []
    policy_decisions: list[dict[str, Any]] = []
    routes = [urljoin(target_url.rstrip("/") + "/", path.lstrip("/")) for path in COMMON_PATHS]
    tech_stack: list[str] = []
    forms: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []

    http_decision = evaluate_agent_action(
        intent_plan=intent_plan,
        token=token,
        action="http.get",
        url=target_url,
    )
    policy_decisions.append(http_decision.as_dict())
    try:
        if not http_decision.allowed:
            raise PermissionError(http_decision.reason)
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            response = await client.get(target_url)
        body = response.text[:8000]
        server = response.headers.get("server")
        powered_by = response.headers.get("x-powered-by")
        if server:
            tech_stack.append(server)
        if powered_by:
            tech_stack.append(powered_by)
        for keyword in ["react", "next.js", "vue", "angular", "graphql", "postgres", "django"]:
            if keyword.lower() in body.lower():
                tech_stack.append(keyword)
        if "<form" in body.lower():
            forms.append({"action": target_url, "method": "get_or_post"})
        for match in re.findall(r'name=["\']([^"\']+)["\']', body, flags=re.IGNORECASE):
            inputs.append({"name": match})
        observations.append(
            {
                "url": str(response.url),
                "status_code": response.status_code,
                "headers": {
                    "server": server,
                    "x-powered-by": powered_by,
                    "content-type": response.headers.get("content-type"),
                },
                "body_excerpt": body[:1200],
            }
        )
        for support_path in ["robots.txt", "sitemap.xml"]:
            try:
                support_url = urljoin(target_url.rstrip("/") + "/", support_path)
                support_response = await client.get(support_url)
                if support_response.status_code < 400:
                    observations.append(
                        {
                            "url": str(support_response.url),
                            "status_code": support_response.status_code,
                            "body_excerpt": support_response.text[:1200],
                        }
                    )
                    if support_path == "sitemap.xml":
                        routes.extend(re.findall(r"<loc>(.*?)</loc>", support_response.text, flags=re.IGNORECASE))
            except Exception as exc:
                observations.append({"url": support_path, "error": str(exc)})
    except Exception as exc:
        observations.append({"url": target_url, "error": str(exc)})

    browser_recon = await run_browser_recon(target_url, intent_plan=intent_plan, token=token)
    policy_decisions.extend(browser_recon.get("policy_decisions", []))
    routes.extend(browser_recon["routes"])
    forms.extend(browser_recon["forms"])
    inputs.extend(browser_recon["inputs"])

    return {
        "discovered_routes": list(dict.fromkeys(routes)),
        "discovered_forms": forms,
        "discovered_inputs": inputs[:20],
        "browser_observations": browser_recon["observations"],
        "browser_errors": browser_recon["errors"],
        "policy_decisions": policy_decisions,
        "technology_stack": list(dict.fromkeys([item for item in tech_stack if item])),
        "http_observations": observations,
    }


def fallback_analysis(state: ScanState) -> list[FindingDraft]:
    drafts: list[FindingDraft] = []
    host = _host_label(state["target_url"])
    headers = " ".join(str(obs.get("headers", {})) for obs in state["http_observations"])
    engine_text = " ".join(
        f"{finding.get('title')} {finding.get('summary')} {finding.get('evidence')}"
        for finding in state.get("engine_findings", [])
    )

    if "x-powered-by" in headers.lower() or "server" in headers.lower():
        drafts.append(
            {
                "id": "header-disclosure",
                "title": "Technology fingerprint disclosure",
                "severity": "low",
                "cwe_id": "CWE-200",
                "url": state["target_url"],
                "parameter": None,
                "payload": None,
                "evidence": headers[:500],
                "confidence": 0.82,
                "reproduction_steps": [f"Send a GET request to {state['target_url']}", "Inspect response headers"],
                "rationale": "Response metadata exposes implementation details that help attackers profile the stack.",
            }
        )

    if _route_is_present(state["discovered_routes"], "/admin"):
        drafts.append(
            {
                "id": "admin-surface",
                "title": "Administrative route exposed in public attack surface",
                "severity": "medium",
                "cwe_id": "CWE-668",
                "url": f"{state['target_url'].rstrip('/')}/admin",
                "parameter": None,
                "payload": None,
                "evidence": f"Recon identified /admin while scanning {host}.",
                "confidence": 0.64,
                "reproduction_steps": [
                    f"Browse to {state['target_url'].rstrip('/')}/admin",
                    "Verify whether unauthenticated access is blocked and whether content leaks."
                ],
                "rationale": "Publicly reachable admin surfaces deserve explicit validation for auth and information leakage.",
            }
        )

    if _has_search_surface(state):
        drafts.append(
            {
                "id": "reflected-input-check",
                "title": "Reflected input surface requires XSS validation",
                "severity": "medium",
                "cwe_id": "CWE-79",
                "url": f"{state['target_url'].rstrip('/')}/search?q=armorscan-probe",
                "parameter": "q",
                "payload": "armorscan-probe",
                "evidence": "Search-like interaction detected in passive reconnaissance.",
                "confidence": 0.58,
                "reproduction_steps": [
                    f"Request {state['target_url'].rstrip('/')}/search?q=armorscan-probe",
                    "Inspect whether the probe value is reflected without output encoding."
                ],
                "rationale": "Search inputs are common XSS candidates when user-controlled data is echoed in HTML.",
            }
        )

    if any("password" in str(item).lower() for item in state["discovered_inputs"]):
        drafts.append(
            {
                "id": "auth-form-hardening",
                "title": "Authentication form requires browser-flow validation",
                "severity": "medium",
                "cwe_id": "CWE-287",
                "url": state["target_url"],
                "parameter": "password",
                "payload": None,
                "evidence": "Playwright discovered password-like inputs in the rendered page.",
                "confidence": 0.61,
                "reproduction_steps": [
                    f"Open {state['target_url']} in a browser",
                    "Inspect login controls and verify rate limiting, autocomplete policy, and error handling.",
                ],
                "rationale": "Rendered authentication flows need dynamic validation beyond static HTTP fetching.",
            }
        )

    if state["browser_observations"] and (
        state["discovered_forms"] or state["discovered_inputs"] or state.get("discovered_apis")
    ):
        drafts.append(
            {
                "id": "dynamic-ui-surface",
                "title": "Dynamic browser surface discovered",
                "severity": "info",
                "cwe_id": None,
                "url": state["target_url"],
                "parameter": None,
                "payload": None,
                "evidence": "Playwright captured rendered UI controls and accessibility tree data.",
                "confidence": 0.72,
                "reproduction_steps": [
                    f"Open {state['target_url']} with JavaScript enabled",
                    "Review discovered controls and network requests for security-sensitive flows.",
                ],
                "rationale": "Interactive controls expand the attack surface for later authenticated and form-aware scans.",
            }
        )

    if engine_text:
        drafts.append(
            {
                "id": "scanner-engine-correlation",
                "title": "Scanner engine findings require analyst review",
                "severity": "info",
                "cwe_id": None,
                "url": state["target_url"],
                "parameter": None,
                "payload": None,
                "evidence": engine_text[:500],
                "confidence": 0.7,
                "reproduction_steps": [
                    "Review normalized scanner findings in the report.",
                    "Confirm exploitability and business impact before remediation prioritization.",
                ],
                "rationale": "Nuclei/SAST scanner evidence was collected and should be correlated with agent observations.",
            }
        )

    if state["scan_type"] in {"url", "api"}:
        header_blob = headers.lower()
        if "content-security-policy" not in header_blob:
            drafts.append(
                {
                    "id": "missing-csp",
                    "title": "Content Security Policy header is missing",
                    "severity": "medium",
                    "cwe_id": "CWE-693",
                    "url": state["target_url"],
                    "parameter": None,
                    "payload": None,
                    "evidence": headers[:500],
                    "confidence": 0.74,
                    "reproduction_steps": [
                        f"Send a GET request to {state['target_url']}",
                        "Verify whether a Content-Security-Policy response header is returned.",
                    ],
                    "rationale": "Missing CSP reduces defense-in-depth against script injection and unsafe third-party content.",
                }
            )
        if "access-control-allow-origin" in header_blob and "*" in header_blob:
            drafts.append(
                {
                    "id": "cors-wildcard",
                    "title": "Wildcard CORS policy requires review",
                    "severity": "medium",
                    "cwe_id": "CWE-942",
                    "url": state["target_url"],
                    "parameter": None,
                    "payload": None,
                    "evidence": headers[:500],
                    "confidence": 0.69,
                    "reproduction_steps": [
                        f"Send a GET request to {state['target_url']}",
                        "Inspect Access-Control-Allow-Origin and credential settings.",
                    ],
                    "rationale": "Permissive cross-origin sharing can expose sensitive API responses when combined with weak auth controls.",
                }
            )

    if state["scan_type"] == "github":
        repo_text = " ".join(str(obs) for obs in state["http_observations"] + state["browser_observations"]).lower()
        if "dockerfile" in repo_text or "docker-compose" in repo_text:
            drafts.append(
                {
                    "id": "container-review-surface",
                    "title": "Containerized deployment surface discovered",
                    "severity": "info",
                    "cwe_id": None,
                    "url": state["target_url"],
                    "parameter": None,
                    "payload": None,
                    "evidence": repo_text[:500],
                    "confidence": 0.7,
                    "reproduction_steps": [
                        "Review Docker and deployment manifests for exposed services, secrets, and weak defaults.",
                    ],
                    "rationale": "Infrastructure files expand the attack surface and should be reviewed alongside application code.",
                }
            )

    return drafts


def build_report(state: ScanState) -> dict[str, Any]:
    severity_counts: dict[str, int] = {}
    for finding in state["findings"]:
        severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1

    return {
        "scan_id": state["scan_id"],
        "target_url": state["target_url"],
        "scan_type": state["scan_type"],
        "summary": {
            "status": state["status"],
            "routes_discovered": len(state["discovered_routes"]),
            "forms_discovered": len(state["discovered_forms"]),
            "inputs_discovered": len(state["discovered_inputs"]),
            "apis_discovered": len(state.get("discovered_apis", [])),
            "uploads_discovered": len(state.get("discovered_uploads", [])),
            "authenticated_workflows": len(state.get("authenticated_workflows", [])),
            "browser_observations": len(state["browser_observations"]),
            "engine_observations": len(state.get("engine_observations", [])),
            "engine_findings": len(state.get("engine_findings", [])),
            "findings_count": len(state["findings"]),
            "severity_counts": severity_counts,
        },
        "technology_stack": state["technology_stack"],
        "scan_plan": state.get("scan_plan"),
        "browser_errors": state["browser_errors"],
        "engine_observations": state.get("engine_observations", []),
        "engine_findings": state.get("engine_findings", []),
        "engine_errors": state.get("engine_errors", []),
        "discovered_apis": state.get("discovered_apis", []),
        "discovered_uploads": state.get("discovered_uploads", []),
        "discovered_js_endpoints": state.get("discovered_js_endpoints", []),
        "authenticated_workflows": state.get("authenticated_workflows", []),
        "repo_inventory": state.get("repo_inventory", []),
        "dependency_inventory": state.get("dependency_inventory", []),
        "iac_inventory": state.get("iac_inventory", []),
        "scanner_capabilities": state.get("scanner_capabilities", []),
        "normalized_evidence": state.get("normalized_evidence", []),
        "correlation_summary": state.get("correlation_summary"),
        "retest_plan": state.get("retest_plan"),
        "intent_plan": state["intent_plan"],
        "policy_decisions": state["policy_decisions"],
        "evidence_summary": state.get("evidence_summary"),
        "findings": state["findings"],
        "agent_trace": state["agent_trace"],
    }


llm_client = GroqResponsesClient()
