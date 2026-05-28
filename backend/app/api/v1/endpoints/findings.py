from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.api.v1.schemas import (
    BulkFindingStatusUpdate,
    FindingCommentCreateRequest,
    FindingCommentRead,
    FindingDetailRead,
    FindingEvidenceCreateRequest,
    FindingEvidenceRead,
    FindingRead,
    FindingStatusUpdate,
    FindingSuppressionCreateRequest,
    FindingSuppressionRead,
    RemediationHistoryRead,
)
from app.core.database import get_db
from app.models import (
    AuditEvent,
    Finding,
    FindingComment,
    FindingEvidence,
    FindingSuppression,
    RemediationHistory,
    Scan,
    User,
)
from app.services.access_control import scan_access_filter

router = APIRouter()


@router.get("/", response_model=list[FindingRead])
async def list_findings(
    severity: str | None = Query(default=None),
    risk_rating: str | None = Query(default=None),
    status: str | None = Query(default=None),
    scan_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Finding)
        .join(Finding.scan)
        .where(scan_access_filter(current_user))
        .order_by(Finding.risk_score.desc(), Finding.created_at.desc())
    )
    if severity:
        stmt = stmt.where(Finding.severity == severity)
    if risk_rating:
        stmt = stmt.where(Finding.risk_rating == risk_rating)
    if status:
        stmt = stmt.where(Finding.status == status)
    if scan_id:
        stmt = stmt.where(Finding.scan_id == scan_id)

    result = await db.execute(stmt)
    return [FindingRead.model_validate(finding) for finding in result.scalars().all()]


async def _load_finding_for_user(
    finding_id: str, db: AsyncSession, current_user: User, *, with_details: bool = False
) -> Finding:
    stmt = select(Finding).join(Finding.scan).where(Finding.id == finding_id, scan_access_filter(current_user))
    if with_details:
        stmt = stmt.options(
            selectinload(Finding.scan),
            selectinload(Finding.evidence),
            selectinload(Finding.comments),
            selectinload(Finding.suppressions),
            selectinload(Finding.remediation_history),
        )
    else:
        stmt = stmt.options(selectinload(Finding.scan))
    result = await db.execute(stmt)
    finding = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.get("/{finding_id}", response_model=FindingDetailRead)
async def get_finding(
    finding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    finding = await _load_finding_for_user(finding_id, db, current_user, with_details=True)
    return FindingDetailRead.model_validate(finding)


@router.patch("/{finding_id}/status", response_model=FindingRead)
async def update_finding_status(
    finding_id: str,
    payload: FindingStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    finding = await _load_finding_for_user(finding_id, db, current_user)

    previous_status = finding.status
    finding.status = payload.status
    db.add(
        RemediationHistory(
            finding_id=finding.id,
            actor_id=current_user.id,
            from_status=previous_status,
            to_status=payload.status,
            note=payload.note,
            metadata_json={},
        )
    )
    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=finding.scan.target_id,
            scan_id=finding.scan_id,
            event_type="finding.status_updated",
            message=f"Finding {finding.id} marked as {payload.status}",
            details={"finding_id": finding.id, "from_status": previous_status, "status": payload.status},
        )
    )
    await db.commit()
    await db.refresh(finding)
    return FindingRead.model_validate(finding)


@router.patch("/bulk-status", response_model=list[FindingRead])
async def bulk_update_finding_status(
    payload: BulkFindingStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Finding)
        .options(selectinload(Finding.scan))
        .join(Finding.scan)
        .where(Finding.id.in_(payload.finding_ids), scan_access_filter(current_user))
    )
    findings = result.scalars().all()
    for finding in findings:
        previous_status = finding.status
        finding.status = payload.status
        db.add(
            RemediationHistory(
                finding_id=finding.id,
                actor_id=current_user.id,
                from_status=previous_status,
                to_status=payload.status,
                note=payload.note,
                metadata_json={"bulk": True},
            )
        )
    await db.commit()
    for finding in findings:
        await db.refresh(finding)
    return [FindingRead.model_validate(finding) for finding in findings]


@router.get("/{finding_id}/evidence", response_model=list[FindingEvidenceRead])
async def list_evidence(
    finding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _load_finding_for_user(finding_id, db, current_user)
    result = await db.execute(
        select(FindingEvidence)
        .where(FindingEvidence.finding_id == finding_id)
        .order_by(FindingEvidence.created_at.desc())
    )
    return [FindingEvidenceRead.model_validate(item) for item in result.scalars().all()]


@router.post("/{finding_id}/evidence", response_model=FindingEvidenceRead)
async def create_evidence(
    finding_id: str,
    payload: FindingEvidenceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    finding = await _load_finding_for_user(finding_id, db, current_user)
    evidence = FindingEvidence(
        finding_id=finding.id,
        evidence_type=payload.evidence_type,
        title=payload.title,
        content=payload.content,
        artifact_uri=payload.artifact_uri,
        metadata_json=payload.metadata_json,
        created_by_id=current_user.id,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return FindingEvidenceRead.model_validate(evidence)


@router.post("/{finding_id}/comments", response_model=FindingCommentRead)
async def create_comment(
    finding_id: str,
    payload: FindingCommentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    finding = await _load_finding_for_user(finding_id, db, current_user)
    comment = FindingComment(finding_id=finding.id, author_id=current_user.id, body=payload.body)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return FindingCommentRead.model_validate(comment)


@router.post("/{finding_id}/suppressions", response_model=FindingSuppressionRead)
async def create_suppression(
    finding_id: str,
    payload: FindingSuppressionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    finding = await _load_finding_for_user(finding_id, db, current_user)
    previous_status = finding.status
    suppression = FindingSuppression(
        finding_id=finding.id,
        created_by_id=current_user.id,
        reason=payload.reason,
        status="active",
        expires_at=payload.expires_at,
    )
    finding.status = "ignored"
    db.add(suppression)
    db.add(
        RemediationHistory(
            finding_id=finding.id,
            actor_id=current_user.id,
            from_status=previous_status,
            to_status="ignored",
            note=payload.reason,
            metadata_json={"suppression": True},
        )
    )
    await db.commit()
    await db.refresh(suppression)
    return FindingSuppressionRead.model_validate(suppression)


@router.get("/{finding_id}/history", response_model=list[RemediationHistoryRead])
async def list_remediation_history(
    finding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _load_finding_for_user(finding_id, db, current_user)
    result = await db.execute(
        select(RemediationHistory)
        .where(RemediationHistory.finding_id == finding_id)
        .order_by(RemediationHistory.created_at.desc())
    )
    return [RemediationHistoryRead.model_validate(item) for item in result.scalars().all()]
