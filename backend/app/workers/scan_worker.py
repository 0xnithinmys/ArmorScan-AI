from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models import AgentExecutionLog, AuditEvent, Finding, FindingEvidence, Scan, ScanArtifact
from app.services.event_bus import publish_scan_event
from app.services.risk import build_risk_report, enrich_findings_with_risk

logger = logging.getLogger(__name__)
_worker_local = threading.local()

AGENTS_DIR = Path(__file__).resolve().parents[3] / "agents"
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))


def _initial_state(scan_id: str, target_url: str, scan_type: str) -> dict:
    return {
        "scan_id": scan_id,
        "target_url": target_url,
        "scan_type": scan_type,
        "status": "idle",
        "scan_plan": None,
        "discovered_routes": [],
        "discovered_forms": [],
        "discovered_inputs": [],
        "discovered_apis": [],
        "discovered_uploads": [],
        "discovered_js_endpoints": [],
        "authenticated_workflows": [],
        "repo_inventory": [],
        "dependency_inventory": [],
        "iac_inventory": [],
        "browser_observations": [],
        "browser_errors": [],
        "technology_stack": [],
        "state_graph": None,
        "engine_observations": [],
        "engine_findings": [],
        "engine_errors": [],
        "scanner_capabilities": [],
        "normalized_evidence": [],
        "correlation_summary": None,
        "retest_plan": None,
        "evidence_summary": None,
        "intent_plan": None,
        "armoriq_token": None,
        "policy_decisions": [],
        "http_observations": [],
        "findings_drafts": [],
        "findings": [],
        "report_json": None,
        "agent_trace": [],
        "error": None,
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _clean_state_for_storage(state: dict) -> dict:
    cleaned = dict(state)
    for key in ("agent_trace", "report_json", "policy_decisions", "findings"):
        if key in cleaned:
            cleaned[key] = _json_safe(cleaned[key])
    return cleaned


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    loop = getattr(_worker_local, "loop", None)
    if loop is not None and not loop.is_closed():
        return loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _worker_local.loop = loop
    return loop


def _run_worker_coro(coro):
    loop = _get_worker_loop()
    return loop.run_until_complete(coro)


def _scan_event(scan_id: str, state: dict) -> dict[str, Any]:
    trace = (state.get("agent_trace") or [{}])[-1]
    return _json_safe(
        {
            "type": "scan.progress",
            "scan_id": scan_id,
            "status": state.get("status"),
            "node": trace.get("node") or trace.get("agent") or "workflow",
            "summary": trace.get("summary") or state.get("summary"),
            "details": trace.get("details") or {},
            "trace": trace,
            "findings_count": len(state.get("findings") or []),
            "engine_findings_count": len(state.get("engine_findings") or []),
            "policy_decisions_count": len(state.get("policy_decisions") or []),
            "report_ready": bool(state.get("report_json")),
        }
    )


async def _persist_scan_progress(scan_id: str, state: dict) -> None:
    state = _clean_state_for_storage(state)
    async with AsyncSessionLocal() as session:
        scan = await session.get(Scan, scan_id)
        if scan is None:
            return

        scan.status = state["status"]
        scan.agent_trace = state["agent_trace"]
        scan.report_json = state.get("report_json")
        scan.policy_decisions = state.get("policy_decisions", scan.policy_decisions)
        if state["agent_trace"]:
            scan.summary = state["agent_trace"][-1]["summary"]
            trace = state["agent_trace"][-1]
            session.add(
                AgentExecutionLog(
                    scan_id=scan_id,
                    agent_name=str(trace.get("agent") or "workflow"),
                    stage=str(state.get("status") or trace.get("stage") or "unknown"),
                    status=str(state.get("status") or "running"),
                    message=str(trace.get("summary") or ""),
                    metadata_json=_json_safe({"trace": trace}),
                )
            )
        await session.commit()


async def _persist_final_results(scan_id: str, state: dict) -> None:
    state = _clean_state_for_storage(state)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Scan).options(selectinload(Scan.target)).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        if scan is None:
            return

        risk_findings = enrich_findings_with_risk(state["findings"])
        state = {**state, "findings": risk_findings}
        state_report = state.get("report_json") or {}
        state["report_json"] = {
            **state_report,
            "risk_report": build_risk_report(
                scan={
                    "id": scan.id,
                    "status": state["status"],
                    "scan_type": scan.scan_type,
                    "created_at": scan.created_at.isoformat() if scan.created_at else None,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
                target={
                    "id": scan.target_id,
                    "target_url": scan.target.target_url if scan.target else None,
                    "scope": scan.scope,
                },
                findings=risk_findings,
            ),
        }
        state = _clean_state_for_storage(state)

        scan.status = state["status"]
        scan.agent_trace = state["agent_trace"]
        scan.report_json = state.get("report_json")
        scan.policy_decisions = state.get("policy_decisions", [])
        summary = state.get("report_json", {}).get("summary", {})
        scan.summary = (
            f"Governed scan completed with {summary.get('findings_count', 0)} findings, "
            f"{summary.get('engine_findings', 0)} scanner findings, "
            f"and {summary.get('routes_discovered', 0)} routes."
        )
        scan.completed_at = datetime.now(timezone.utc)

        existing_findings = (
            await session.execute(select(Finding).where(Finding.scan_id == scan_id))
        ).scalars().all()
        for finding in existing_findings:
            await session.delete(finding)

        for finding_data in state["findings"]:
            finding = Finding(
                scan_id=scan_id,
                severity=finding_data["severity"],
                title=finding_data["title"],
                location=finding_data["location"],
                confidence=finding_data["confidence"],
                risk_score=finding_data["risk_score"],
                risk_rating=finding_data["risk_rating"],
                status="open",
                summary=finding_data["summary"],
                business_impact=finding_data["business_impact"],
                remediation=finding_data["remediation"],
                risk_factors=finding_data["risk_factors"],
                reproduction_steps=finding_data["reproduction_steps"],
            )
            session.add(finding)
            await session.flush()
            session.add(
                FindingEvidence(
                    finding_id=finding.id,
                    evidence_type="agent_summary",
                    title="Agent finding summary",
                    content=finding.summary,
                    metadata_json=_json_safe(
                        {
                            "location": finding.location,
                            "risk_factors": finding.risk_factors,
                            "reproduction_steps": finding.reproduction_steps,
                        }
                    ),
                )
            )

        session.add(
            ScanArtifact(
                scan_id=scan_id,
                artifact_type="risk_report",
                name="Risk report JSON",
                uri=None,
                content_type="application/json",
                metadata_json=_json_safe({"summary": state["report_json"].get("summary", {})}),
            )
        )

        session.add(
            AuditEvent(
                scan_id=scan_id,
                target_id=scan.target_id,
                user_id=scan.requested_by_id,
                event_type="scan.workflow_completed",
                message="Governed agent workflow completed with scanner engines and findings were persisted.",
                details=_json_safe({
                    "findings": len(state["findings"]),
                    "engine_findings": len(state.get("engine_findings", [])),
                    "policy_decisions": len(scan.policy_decisions),
                }),
            )
        )
        await session.commit()


async def _mark_scan_failed(scan_id: str, error: str) -> None:
    public_error = _public_scan_error(error)
    async with AsyncSessionLocal() as session:
        scan = await session.get(Scan, scan_id)
        if scan is None:
            return
        scan.status = "failed"
        scan.summary = public_error
        scan.completed_at = datetime.now(timezone.utc)
        session.add(
            AuditEvent(
                scan_id=scan_id,
                target_id=scan.target_id,
                user_id=scan.requested_by_id,
                event_type="scan.workflow_failed",
                message="Governed workflow failed.",
                details=_json_safe({"error": error, "public_error": public_error}),
            )
        )
        await session.commit()


def _public_scan_error(error: str) -> str:
    lower = error.lower()
    if "different loop" in lower or "event loop is closed" in lower:
        return "Scan worker event loop recovered after an internal async resource error. Please retry the scan."
    if "json serializable" in lower or "autoflush" in lower:
        return "Scan completed but report persistence hit a serialization error. Please retry the scan."
    return f"Scan failed during governed workflow: {error}"


async def _run_scan_async(scan_id: str, target_url: str, scan_type: str) -> dict:
    from armorscan.graph import run_scan_workflow

    initial_state = _initial_state(scan_id, target_url, scan_type)
    async with AsyncSessionLocal() as session:
        scan = await session.get(Scan, scan_id)
        if scan is not None:
            initial_state["armoriq_token"] = scan.armoriq_token
            initial_state["intent_plan"] = scan.intent_plan
            initial_state["policy_decisions"] = scan.policy_decisions or []

    states = await run_scan_workflow(initial_state)
    for state in states:
        state = _clean_state_for_storage(state)
        await _persist_scan_progress(scan_id, state)
        await publish_scan_event(scan_id, _scan_event(scan_id, state))

    final_state = states[-1]
    if final_state["status"] == "failed":
        await _mark_scan_failed(scan_id, final_state.get("error") or "Agent workflow failed.")
        return {
            "scan_id": scan_id,
            "status": "failed",
            "findings_count": len(final_state.get("findings", [])),
            "message": final_state.get("error") or "Agent workflow failed.",
        }

    await _persist_final_results(scan_id, final_state)
    await publish_scan_event(
        scan_id,
        {
            **_scan_event(scan_id, final_state),
            "type": "scan.completed",
            "status": "completed",
            "report_ready": True,
        },
    )
    return {
        "scan_id": scan_id,
        "status": final_state["status"],
        "findings_count": len(final_state["findings"]),
        "message": "Governed LangGraph workflow completed.",
    }


@celery_app.task(bind=True, name="app.workers.scan_worker.run_scan", max_retries=2)
def run_scan(self, scan_id: str, target_url: str, scan_type: str = "url"):
    logger.info("[Scan %s] Starting governed workflow for %s", scan_id, target_url)

    try:
        return _run_worker_coro(_run_scan_async(scan_id, target_url, scan_type))
    except Exception as exc:  # pragma: no cover
        logger.exception("[Scan %s] Failed", scan_id)
        error = str(exc)
        try:
            _run_worker_coro(_mark_scan_failed(scan_id, error))
            _run_worker_coro(
                publish_scan_event(
                    scan_id,
                    {
                        "type": "scan.failed",
                        "scan_id": scan_id,
                        "status": "failed",
                        "summary": _public_scan_error(error),
                        "error": error,
                    },
                )
            )
        except Exception as inner_exc:
            logger.error("Failed to run failure handlers: %s", inner_exc)
        return {
            "scan_id": scan_id,
            "status": "failed",
            "message": _public_scan_error(error),
        }
