from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import AuditEvent, Scan, User

router = APIRouter()


async def _load_scan_for_user(scan_id: str, db: AsyncSession, user: User) -> Scan:
    result = await db.execute(
        select(Scan)
        .options(selectinload(Scan.target), selectinload(Scan.findings))
        .where(Scan.id == scan_id, Scan.requested_by_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/pdf")
async def download_pdf(scan_id: str):
    return {
        "scan_id": scan_id,
        "available": False,
        "message": "PDF export is scheduled for Phase 8 reporting.",
    }


@router.get("/{scan_id}/sarif")
async def download_sarif(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await _load_scan_for_user(scan_id, db, current_user)
    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "ArmorScan AI", "version": "0.1.0"}},
                "results": [
                    {
                        "ruleId": finding.severity.lower(),
                        "level": "error" if finding.severity.lower() in {"critical", "high"} else "warning",
                        "message": {"text": finding.title},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": scan.target.target_url},
                                    "region": {"snippet": {"text": finding.location}},
                                }
                            }
                        ],
                    }
                    for finding in scan.findings
                ],
            }
        ],
    }


@router.get("/{scan_id}/json")
async def download_json(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await _load_scan_for_user(scan_id, db, current_user)
    audit_result = await db.execute(
        select(AuditEvent).where(AuditEvent.scan_id == scan.id).order_by(AuditEvent.created_at.asc())
    )
    return {
        "scan": {
            "id": scan.id,
            "status": scan.status,
            "scan_type": scan.scan_type,
            "summary": scan.summary,
            "report_json": scan.report_json,
            "agent_trace": scan.agent_trace,
            "created_at": scan.created_at,
            "completed_at": scan.completed_at,
        },
        "target": {
            "id": scan.target.id,
            "name": scan.target.name,
            "target_type": scan.target.target_type,
            "target_url": scan.target.target_url,
            "scope": scan.target.scope,
        },
        "findings": [
            {
                "id": finding.id,
                "severity": finding.severity,
                "title": finding.title,
                "location": finding.location,
                "confidence": finding.confidence,
                "status": finding.status,
                "summary": finding.summary,
                "reproduction_steps": finding.reproduction_steps,
            }
            for finding in scan.findings
        ],
        "audit_events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "message": event.message,
                "details": event.details,
                "created_at": event.created_at,
            }
            for event in audit_result.scalars().all()
        ],
    }
