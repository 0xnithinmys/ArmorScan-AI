from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.api.v1.schemas import FindingRead, FindingStatusUpdate
from app.core.database import get_db
from app.models import AuditEvent, Finding, Scan, User

router = APIRouter()


@router.get("/", response_model=list[FindingRead])
async def list_findings(
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    scan_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Finding)
        .join(Finding.scan)
        .where(Scan.requested_by_id == current_user.id)
        .order_by(Finding.created_at.desc())
    )
    if severity:
        stmt = stmt.where(Finding.severity == severity)
    if status:
        stmt = stmt.where(Finding.status == status)
    if scan_id:
        stmt = stmt.where(Finding.scan_id == scan_id)

    result = await db.execute(stmt)
    return [FindingRead.model_validate(finding) for finding in result.scalars().all()]


@router.patch("/{finding_id}/status", response_model=FindingRead)
async def update_finding_status(
    finding_id: str,
    payload: FindingStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Finding)
        .options(selectinload(Finding.scan))
        .join(Finding.scan)
        .where(Finding.id == finding_id, Scan.requested_by_id == current_user.id)
    )
    finding = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding.status = payload.status
    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=finding.scan.target_id,
            scan_id=finding.scan_id,
            event_type="finding.status_updated",
            message=f"Finding {finding.id} marked as {payload.status}",
            details={"finding_id": finding.id, "status": payload.status},
        )
    )
    return FindingRead.model_validate(finding)
