"""
ArmorScan AI - Phase 4 LangGraph workflow.

This module uses a sequential fallback runner so local development still works
even when `langgraph` is not installed yet. When the dependency is available,
`build_graph()` also returns a compiled LangGraph graph for parity with the
project architecture.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

import httpx

from armorscan.evidence import build_evidence_summary
from armorscan.findings import clamp_confidence, dedupe_findings, normalize_draft
from armorscan.planning import build_scan_plan
from armorscan.runtime import build_report, fallback_analysis, llm_client, passive_recon
from armorscan.state import FindingDraft, ScanState
from armorscan.tools.scanning_engines import run_scanning_engines

try:
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover - optional runtime dependency
    END = "__end__"
    StateGraph = None


def append_trace(state: ScanState, *, node: str, summary: str, status: str, details: dict[str, Any]) -> ScanState:
    next_state = deepcopy(state)
    next_state["agent_trace"] = state["agent_trace"] + [
        {"node": node, "status": status, "summary": summary, "details": details}
    ]
    next_state["status"] = status
    return next_state


async def planner_node(state: ScanState) -> ScanState:
    next_state = deepcopy(state)
    next_state["scan_plan"] = build_scan_plan(next_state)
    next_state["status"] = "planning"
    return append_trace(
        next_state,
        node="planner",
        status="planning",
        summary="Governed scan plan prepared",
        details={
            "phases": [phase["name"] for phase in next_state["scan_plan"]["phases"]],
            "allowed_actions": next_state["scan_plan"]["allowed_actions"],
        },
    )


async def recon_node(state: ScanState) -> ScanState:
    recon = await passive_recon(
        state["target_url"],
        intent_plan=state["intent_plan"],
        token=state["armoriq_token"],
    )
    next_state = deepcopy(state)
    next_state.update(recon)
    next_state["policy_decisions"] = state["policy_decisions"] + recon.get("policy_decisions", [])
    if not next_state["intent_plan"]:
        next_state["intent_plan"] = {
            "mode": "passive-and-safe-validation",
            "steps": [
                "Map reachable public routes",
                "Render target in Chromium and extract accessibility tree",
                "Capture forms, inputs, links, buttons, and browser network activity",
                "Infer technology stack from headers and markup",
                "Draft candidate findings",
                "Run safe HTTP confirmation probes",
            ],
        }
    next_state["status"] = "planning"
    return append_trace(
        next_state,
        node="recon",
        status="planning",
        summary="Reconnaissance completed",
        details={
            "routes": len(next_state["discovered_routes"]),
            "forms": len(next_state["discovered_forms"]),
            "inputs": len(next_state["discovered_inputs"]),
            "browser_observations": len(next_state["browser_observations"]),
            "browser_errors": next_state["browser_errors"],
            "policy_decisions": len(next_state["policy_decisions"]),
            "technology_stack": next_state["technology_stack"],
        },
    )


async def analysis_node(state: ScanState) -> ScanState:
    drafts: list[FindingDraft] = fallback_analysis(state)

    schema = {
        "name": "armorscan_finding_drafts",
        "schema": {
            "type": "object",
            "properties": {
                "findings_drafts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "severity": {"type": "string"},
                            "cwe_id": {"type": ["string", "null"]},
                            "url": {"type": "string"},
                            "parameter": {"type": ["string", "null"]},
                            "payload": {"type": ["string", "null"]},
                            "evidence": {"type": ["string", "null"]},
                            "confidence": {"type": "number"},
                            "reproduction_steps": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "rationale": {"type": ["string", "null"]},
                        },
                        "required": [
                            "id",
                            "title",
                            "severity",
                            "cwe_id",
                            "url",
                            "parameter",
                            "payload",
                            "evidence",
                            "confidence",
                            "reproduction_steps",
                            "rationale",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["findings_drafts"],
            "additionalProperties": False,
        },
    }
    instructions = (
        "You are ArmorScan AI's vulnerability analysis agent. Draft only defensive, "
        "safe validation ideas based on the reconnaissance data. Never suggest destructive "
        "payloads, persistence, brute force, or exfiltration. Focus on likely OWASP-style web "
        "issues that can be checked with harmless HTTP probes."
    )
    input_text = (
        f"Target: {state['target_url']}\n"
        f"Scan type: {state['scan_type']}\n"
        f"Scan plan: {state.get('scan_plan')}\n"
        f"Routes: {state['discovered_routes']}\n"
        f"Inputs: {state['discovered_inputs']}\n"
        f"Forms: {state['discovered_forms']}\n"
        f"Tech: {state['technology_stack']}\n"
        f"Observations: {state['http_observations']}\n"
        f"Browser observations: {state['browser_observations']}\n"
        f"Browser errors: {state['browser_errors']}\n"
        f"Scanner observations: {state.get('engine_observations', [])}\n"
        f"Scanner findings: {state.get('engine_findings', [])}\n"
        f"Scanner errors: {state.get('engine_errors', [])}\n"
        "Return up to 5 candidate findings."
    )

    try:
        groq_response = await llm_client.create_structured_response(
            instructions=instructions,
            input_text=input_text,
            json_schema=schema,
        )
        if groq_response and groq_response.get("findings_drafts"):
            drafts = [
                draft
                for draft in groq_response["findings_drafts"]
                if isinstance(draft, dict) and normalize_draft(draft, fallback_url=state["target_url"])
            ]
    except Exception as exc:
        state = append_trace(
            state,
            node="analysis_warning",
            status=state["status"],
            summary="Groq analysis fallback activated",
            details={"reason": str(exc)},
        )

    next_state = deepcopy(state)
    next_state["findings_drafts"] = drafts
    next_state["status"] = "observing"
    return append_trace(
        next_state,
        node="analysis",
        status="observing",
        summary="Candidate findings drafted",
        details={"draft_count": len(drafts)},
    )


async def engines_node(state: ScanState) -> ScanState:
    engine_output = await run_scanning_engines(state)
    next_state = deepcopy(state)
    next_state["engine_observations"] = engine_output["engine_observations"]
    next_state["engine_findings"] = engine_output["engine_findings"]
    next_state["engine_errors"] = engine_output["engine_errors"]
    next_state["policy_decisions"] = state["policy_decisions"] + engine_output["policy_decisions"]
    next_state["status"] = "executing"
    return append_trace(
        next_state,
        node="engines",
        status="executing",
        summary="Scanner engines completed",
        details={
            "observations": len(next_state["engine_observations"]),
            "findings": len(next_state["engine_findings"]),
            "errors": next_state["engine_errors"],
            "policy_decisions": len(next_state["policy_decisions"]),
        },
    )


async def exploit_node(state: ScanState) -> ScanState:
    confirmed_findings: list[dict[str, Any]] = [dict(finding) for finding in state.get("engine_findings", [])]
    observations = list(state["http_observations"])
    policy_decisions = list(state["policy_decisions"])

    for draft in state["findings_drafts"]:
        normalized_draft = normalize_draft(draft, fallback_url=state["target_url"])
        if normalized_draft is None:
            continue
        confidence = normalized_draft["confidence"]
        evidence = draft.get("evidence")
        if draft.get("parameter") and draft.get("payload") and state["scan_type"] == "url":
            from armorscan.policy import evaluate_agent_action

            probe_url = str(normalized_draft["location"])
            decision = evaluate_agent_action(
                intent_plan=state["intent_plan"],
                token=state["armoriq_token"],
                action="http.get",
                url=probe_url,
                payload=draft.get("payload"),
            )
            policy_decisions.append(decision.as_dict())
            if not decision.allowed:
                observations.append({"url": probe_url, "blocked_by_policy": decision.reason})
                continue
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    response = await client.get(probe_url)
                body_excerpt = response.text[:2000]
                observations.append(
                    {
                        "url": str(response.url),
                        "status_code": response.status_code,
                        "body_excerpt": body_excerpt[:500],
                    }
                )
                if draft["payload"] in body_excerpt:
                    confidence = min(98, confidence + 22)
                    evidence = f"Payload reflected in response excerpt: {draft['payload']}"
            except Exception as exc:
                observations.append({"url": probe_url, "error": str(exc)})

        if confidence >= 55:
            confirmed_findings.append(
                {
                    "id": normalized_draft["id"],
                    "title": normalized_draft["title"],
                    "severity": normalized_draft["severity"],
                    "cwe_id": normalized_draft.get("cwe_id"),
                    "location": normalized_draft["location"],
                    "parameter": normalized_draft.get("parameter"),
                    "payload": normalized_draft.get("payload"),
                    "evidence": evidence,
                    "confidence": clamp_confidence(confidence),
                    "summary": normalized_draft["summary"],
                    "reproduction_steps": normalized_draft.get("reproduction_steps", []),
                    "source": normalized_draft["source"],
                }
            )

    next_state = deepcopy(state)
    next_state["http_observations"] = observations
    next_state["policy_decisions"] = policy_decisions
    next_state["findings"] = dedupe_findings(confirmed_findings)
    next_state["evidence_summary"] = build_evidence_summary(next_state)
    next_state["status"] = "reflecting"
    return append_trace(
        next_state,
        node="exploit",
        status="reflecting",
        summary="Safe validation completed",
        details={
            "confirmed_findings": len(next_state["findings"]),
            "engine_findings": len(state.get("engine_findings", [])),
        },
    )


async def reporter_node(state: ScanState) -> ScanState:
    next_state = deepcopy(state)
    next_state["evidence_summary"] = build_evidence_summary(next_state)
    next_state["status"] = "completed"
    next_state = append_trace(
        next_state,
        node="reporter",
        status="completed",
        summary="Report synthesized",
        details={"findings": len(next_state["findings"])},
    )
    next_state["report_json"] = build_report(next_state)
    return next_state


NODE_PIPELINE: list[tuple[str, Callable[[ScanState], Any]]] = [
    ("planner", planner_node),
    ("recon", recon_node),
    ("engines", engines_node),
    ("analysis", analysis_node),
    ("exploit", exploit_node),
    ("reporter", reporter_node),
]


async def run_scan_workflow(initial_state: ScanState) -> list[ScanState]:
    states: list[ScanState] = []
    current = deepcopy(initial_state)
    current["state_graph"] = {"engine": "langgraph" if armorscan_graph is not None else "sequential"}
    for node_name, node in NODE_PIPELINE:
        try:
            current = await node(current)
        except Exception as exc:
            failed = deepcopy(current)
            failed["status"] = "failed"
            failed["error"] = str(exc)
            failed = append_trace(
                failed,
                node=node_name,
                status="failed",
                summary=f"{node_name} failed",
                details={"error": str(exc)},
            )
            states.append(failed)
            break
        states.append(current)
    return states


def build_graph():
    if StateGraph is None:
        return None

    graph = StateGraph(ScanState)
    graph.add_node("planner", planner_node)
    graph.add_node("recon", recon_node)
    graph.add_node("engines", engines_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("exploit", exploit_node)
    graph.add_node("reporter", reporter_node)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "recon")
    graph.add_edge("recon", "engines")
    graph.add_edge("engines", "analysis")
    graph.add_edge("analysis", "exploit")
    graph.add_edge("exploit", "reporter")
    graph.add_edge("reporter", END)
    return graph.compile()


armorscan_graph = build_graph()
