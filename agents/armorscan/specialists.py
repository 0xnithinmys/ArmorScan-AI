from __future__ import annotations

from copy import deepcopy
from typing import Any

from armorscan.scanner_registry import normalize_engine_record, scanner_capabilities_for
from armorscan.state import ScanState
from armorscan.tools.api_discovery import discover_api_surface
from armorscan.tools.repo_tools import inspect_repository
from armorscan.tools.supply_chain_tools import inspect_supply_chain


def _merge_unique_dicts(items: list[dict[str, Any]], *, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        key = tuple(str(item.get(name) or "") for name in keys)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


async def browser_workflow_agent(state: ScanState) -> dict[str, Any]:
    observations = state.get("browser_observations", [])
    upload_inputs = []
    workflows = []
    js_sources = []
    for observation in observations:
        upload_inputs.extend(observation.get("uploads", []))
        js_sources.extend({"url": src, "source": observation.get("url")} for src in observation.get("scripts", []))
        controls = observation.get("clickable_surfaces", [])
        if controls:
            workflows.append(
                {
                    "url": observation.get("url"),
                    "title": observation.get("title"),
                    "control_count": len(controls),
                    "navigation_count": len([item for item in controls if item.get("kind") == "navigation"]),
                    "submit_control_count": len(
                        [item for item in controls if item.get("kind") == "form-submit-control"]
                    ),
                    "controls": controls[:20],
                }
            )
    auth_candidates = []
    for form in state.get("discovered_forms", []):
        form_text = str(form).lower()
        if "password" in form_text or "login" in form_text or "signin" in form_text:
            auth_candidates.append({"kind": "form", "form": form})
    for item in state.get("discovered_inputs", []):
        if str(item.get("type") or "").lower() == "password":
            auth_candidates.append({"kind": "input", "input": item})
    if auth_candidates:
        workflows.append(
            {
                "url": state["target_url"],
                "workflow_type": "authentication-candidate",
                "auth_candidates": auth_candidates[:10],
                "requires_user_supplied_session": True,
            }
        )
    return {
        "discovered_uploads": upload_inputs[:50],
        "discovered_js_endpoints": js_sources[:100],
        "authenticated_workflows": workflows[:50],
    }


async def api_discovery_agent(state: ScanState) -> dict[str, Any]:
    if state["scan_type"] not in {"url", "api"}:
        return {"discovered_apis": [], "discovered_js_endpoints": [], "policy_decisions": [], "errors": []}
    return await discover_api_surface(
        state["target_url"],
        routes=state["discovered_routes"],
        browser_observations=state["browser_observations"],
        http_observations=state["http_observations"],
        intent_plan=state["intent_plan"],
        token=state["armoriq_token"],
    )


async def repo_sast_agent(state: ScanState) -> dict[str, Any]:
    if state["scan_type"] != "github":
        return {"repo_inventory": [], "routes": [], "inputs": [], "observations": [], "errors": []}
    repo = await inspect_repository(state["target_url"])
    return {
        "repo_inventory": repo.get("observations", []),
        "routes": repo.get("routes", []),
        "inputs": repo.get("inputs", []),
        "observations": repo.get("observations", []),
        "errors": repo.get("errors", []),
        "technology_stack": list(dict.fromkeys(repo.get("frameworks", []) + repo.get("languages", []))),
        "policy_decisions": repo.get("policy_decisions", []),
    }


async def dependency_supply_chain_agent(state: ScanState) -> dict[str, Any]:
    if state["scan_type"] != "github":
        return {"dependency_inventory": [], "iac_inventory": [], "repo_inventory": [], "errors": []}
    return await inspect_supply_chain(state["target_url"])


def scanner_registry_agent(state: ScanState) -> dict[str, Any]:
    return {"scanner_capabilities": scanner_capabilities_for(state["scan_type"])}


def evidence_normalization_agent(state: ScanState) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    for observation in state.get("http_observations", []):
        evidence.append(
            {
                "source": "http-recon",
                "kind": "http-observation",
                "location": observation.get("url") or observation.get("repo_path") or state["target_url"],
                "summary": observation,
            }
        )
    for observation in state.get("browser_observations", []):
        evidence.append(
            {
                "source": "browser-workflow-agent",
                "kind": "browser-observation",
                "location": observation.get("url") or state["target_url"],
                "summary": {
                    "title": observation.get("title"),
                    "status_code": observation.get("status_code"),
                    "requests": len(observation.get("requests", [])),
                    "responses": len(observation.get("responses", [])),
                    "uploads": observation.get("uploads", []),
                },
            }
        )
    for api in state.get("discovered_apis", []):
        evidence.append(
            {
                "source": "api-discovery-agent",
                "kind": "api-endpoint",
                "location": api.get("url"),
                "summary": api,
            }
        )
    for finding in state.get("engine_findings", []):
        evidence.append(normalize_engine_record(finding, default_source="scanner-engine"))
    return {"normalized_evidence": evidence[:500]}


def correlation_agent(state: ScanState) -> dict[str, Any]:
    next_findings = []
    for finding in state.get("findings", []):
        item = dict(finding)
        sources = {str(item.get("source") or "agent")}
        location = str(item.get("location") or "")
        title_words = set(str(item.get("title") or "").lower().split())
        matched_evidence = []
        for evidence in state.get("normalized_evidence", []):
            evidence_location = str(evidence.get("location") or "")
            evidence_title_words = set(str(evidence.get("title") or "").lower().split())
            if location and location in evidence_location:
                matched_evidence.append(evidence)
                sources.add(str(evidence.get("source") or "evidence"))
            elif title_words and evidence_title_words and title_words.intersection(evidence_title_words):
                matched_evidence.append(evidence)
                sources.add(str(evidence.get("source") or "evidence"))
        confidence_boost = min(15, max(0, len(sources) - 1) * 6)
        item["confidence"] = min(99, int(item.get("confidence", 50)) + confidence_boost)
        item["correlated_sources"] = sorted(sources)
        item["evidence_refs"] = matched_evidence[:5]
        item["validation_state"] = "validated" if confidence_boost >= 6 else "detected"
        next_findings.append(item)

    summary = {
        "finding_count": len(next_findings),
        "validated_count": len([item for item in next_findings if item.get("validation_state") == "validated"]),
        "evidence_count": len(state.get("normalized_evidence", [])),
        "api_count": len(state.get("discovered_apis", [])),
        "workflow_count": len(state.get("authenticated_workflows", [])),
        "scanner_count": len(state.get("scanner_capabilities", [])),
    }
    return {"findings": next_findings, "correlation_summary": summary}


def retest_agent(state: ScanState) -> dict[str, Any]:
    checks = []
    for finding in state.get("findings", []):
        checks.append(
            {
                "finding_id": finding.get("id"),
                "title": finding.get("title"),
                "location": finding.get("location"),
                "safe_retest_action": "repeat-observation",
                "validation_state": finding.get("validation_state", "detected"),
                "expected_fixed_signal": "finding no longer reproduced or scanner no longer reports it",
            }
        )
    return {
        "retest_plan": {
            "mode": "safe-retest",
            "checks": checks[:100],
            "requires_authorized_target": True,
        }
    }


def apply_specialist_result(state: ScanState, result: dict[str, Any]) -> ScanState:
    next_state = deepcopy(state)
    for key, value in result.items():
        if key in {"routes", "discovered_routes"}:
            next_state["discovered_routes"] = list(dict.fromkeys(next_state["discovered_routes"] + list(value)))
        elif key in {"inputs", "discovered_inputs"}:
            next_state["discovered_inputs"] = _merge_unique_dicts(
                next_state["discovered_inputs"] + list(value), keys=("name", "source_file", "id")
            )
        elif key == "policy_decisions":
            next_state["policy_decisions"] = next_state["policy_decisions"] + list(value)
        elif key == "errors":
            next_state["engine_errors"] = next_state["engine_errors"] + [str(item) for item in value]
        elif key == "technology_stack":
            next_state["technology_stack"] = list(dict.fromkeys(next_state["technology_stack"] + list(value)))
        elif key == "findings":
            next_state["findings"] = list(value)
        elif key in next_state:
            existing = next_state.get(key)
            if isinstance(existing, list) and isinstance(value, list):
                next_state[key] = existing + value  # type: ignore[literal-required]
            else:
                next_state[key] = value  # type: ignore[literal-required]
    return next_state
