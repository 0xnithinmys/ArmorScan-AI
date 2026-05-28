from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models import AuditEvent, Finding, Scan
from app.services.event_bus import publish_scan_event
from app.services.risk import build_risk_report, enrich_findings_with_risk

logger = logging.getLogger(__name__)

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
        "browser_observations": [],
        "browser_errors": [],
        "technology_stack": [],
        "state_graph": None,
        "engine_observations": [],
        "engine_findings": [],
        "engine_errors": [],
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


async def _persist_scan_progress(scan_id: str, state: dict) -> None:
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
        await session.commit()


async def _persist_final_results(scan_id: str, state: dict) -> None:
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
                    "created_at": scan.created_at,
                    "completed_at": datetime.now(timezone.utc),
                },
                target={
                    "id": scan.target_id,
                    "target_url": scan.target.target_url if scan.target else None,
                    "scope": scan.scope,
                },
                findings=risk_findings,
            ),
        }

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
            session.add(
                Finding(
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
            )

        session.add(
            AuditEvent(
                scan_id=scan_id,
                target_id=scan.target_id,
                user_id=scan.requested_by_id,
                event_type="scan.workflow_completed",
                message="Governed agent workflow completed with scanner engines and findings were persisted.",
                details={
                    "findings": len(state["findings"]),
                    "engine_findings": len(state.get("engine_findings", [])),
                    "policy_decisions": len(scan.policy_decisions),
                },
            )
        )
        await session.commit()


async def _mark_scan_failed(scan_id: str, error: str) -> None:
    async with AsyncSessionLocal() as session:
        scan = await session.get(Scan, scan_id)
        if scan is None:
            return
        scan.status = "failed"
        scan.summary = error
        scan.completed_at = datetime.now(timezone.utc)
        session.add(
            AuditEvent(
                scan_id=scan_id,
                target_id=scan.target_id,
                user_id=scan.requested_by_id,
                event_type="scan.workflow_failed",
                message="Governed workflow failed.",
                details={"error": error},
            )
        )
        await session.commit()


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
        await _persist_scan_progress(scan_id, state)
        await publish_scan_event(
            scan_id,
            {
                "scan_id": scan_id,
                "status": state["status"],
                "trace": state["agent_trace"][-1],
                "findings_count": len(state["findings"]),
            },
        )

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
        return asyncio.run(_run_scan_async(scan_id, target_url, scan_type))
    except Exception as exc:  # pragma: no cover
        logger.exception("[Scan %s] Failed", scan_id)
        asyncio.run(_mark_scan_failed(scan_id, str(exc)))
        asyncio.run(
            publish_scan_event(
                scan_id,
                {"scan_id": scan_id, "status": "failed", "error": str(exc)},
            )
        )
        raise self.retry(exc=exc, countdown=30)
