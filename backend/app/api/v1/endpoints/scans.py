from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.api.v1.schemas import (
    FindingRead,
    ScanArtifactCreateRequest,
    ScanArtifactRead,
    ScanCreateRequest,
    ScanLifecycleRequest,
    ScanRead,
    TargetRead,
)
from app.core.database import get_db
from app.models import AuditEvent, Scan, ScanArtifact, ScanProfile, Target, User
from app.services.access_control import load_scan_for_user, load_target_for_user, require_org_role, scan_access_filter
from app.services.policy import (
    PolicyViolation,
    build_intent_plan,
    evaluate_scan_request,
    require_allowed,
    sign_intent_plan,
)
from app.services.target_authorization import create_proof_challenge
from app.workers.scan_worker import run_scan

router = APIRouter()


def _target_name_from_url(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host_or_path = parsed.hostname or parsed.path.strip("/\\") or "target"
    return host_or_path[:255]


@router.get("/", response_model=list[ScanRead])
async def list_scans(
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Scan).where(scan_access_filter(current_user)).order_by(Scan.created_at.desc())
    if status_filter:
        stmt = stmt.where(Scan.status == status_filter)

    result = await db.execute(stmt)
    return [ScanRead.model_validate(scan) for scan in result.scalars().all()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def initiate_scan(
    payload: ScanCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.target_id:
        target = await load_target_for_user(
            db, target_id=payload.target_id, user=current_user, min_role="analyst"
        )
    elif payload.target_url:
        await require_org_role(db, organization_id=payload.organization_id, user=current_user, role="analyst")
        target = Target(
            owner_id=current_user.id,
            organization_id=payload.organization_id,
            name=(payload.target_name or "").strip() or _target_name_from_url(payload.target_url),
            target_type=payload.scan_type,
            target_url=payload.target_url,
            scope=payload.scope,
            authorization_status="attested" if payload.authorization_attestation else "pending",
            authorization_proof_type="manual_attestation" if payload.authorization_attestation else None,
            authorization_proof="User attested authorization during scan creation"
            if payload.authorization_attestation
            else None,
        )
        db.add(target)
        await db.flush()
        if payload.authorization_attestation:
            attestation = create_proof_challenge(
                target=target,
                user=current_user,
                proof_type="manual_attestation",
            )
            attestation.status = "attested"
            attestation.submitted_value = "I_AM_AUTHORIZED"
            attestation.verified_at = datetime.now(timezone.utc)
            db.add(attestation)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either target_id or target_url",
        )

    if payload.scan_profile_id:
        profile_result = await db.execute(
            select(ScanProfile).where(ScanProfile.id == payload.scan_profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan profile not found")
        if profile.organization_id and profile.organization_id != target.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Scan profile does not belong to the target organization",
            )
        await require_org_role(
            db, organization_id=profile.organization_id, user=current_user, role="analyst"
        )

    scan = Scan(
        target_id=target.id,
        organization_id=target.organization_id or payload.organization_id,
        requested_by_id=current_user.id,
        scan_profile_id=payload.scan_profile_id,
        scan_type=payload.scan_type,
        scope=payload.scope or target.scope,
        status="queued",
        started_at=datetime.now(timezone.utc),
        summary="Scan accepted by API and queued for worker dispatch.",
        agent_trace=[],
        report_json=None,
    )
    db.add(scan)
    await db.flush()

    policy_decision = evaluate_scan_request(scan=scan, target=target, user=current_user)
    try:
        require_allowed(policy_decision)
    except PolicyViolation as exc:
        db.add(
            AuditEvent(
                user_id=current_user.id,
                target_id=target.id,
                scan_id=scan.id,
                event_type="policy.intent_denied",
                message=exc.decision.reason,
                details=exc.decision.as_dict(),
            )
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.decision.reason) from exc
    scan.intent_plan = build_intent_plan(scan=scan, target=target, user=current_user)
    scan.armoriq_token = sign_intent_plan(scan.intent_plan)
    scan.policy_decisions = [policy_decision.as_dict()]

    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=target.id,
            scan_id=scan.id,
            event_type="policy.intent_signed",
            message="ArmorIQ local policy signed the scan intent plan.",
            details={
                "decision": policy_decision.as_dict(),
                "allowed_hosts": scan.intent_plan["allowed_hosts"],
                "allowed_actions": scan.intent_plan["allowed_actions"],
            },
        )
    )

    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=target.id,
            scan_id=scan.id,
            event_type="scan.created",
            message=f"Scan queued for target {target.target_url}",
            details={"scan_type": scan.scan_type, "scope": scan.scope},
        )
    )

    await db.commit()
    await db.refresh(scan)
    await db.refresh(target)

    try:
        task = run_scan.delay(scan_id=scan.id, target_url=target.target_url, scan_type=scan.scan_type)
        scan.celery_task_id = task.id
        db.add(
            AuditEvent(
                user_id=current_user.id,
                target_id=target.id,
                scan_id=scan.id,
                event_type="scan.dispatched",
                message="Scan dispatched to Celery worker",
                details={"celery_task_id": task.id},
            )
        )
        await db.commit()
        await db.refresh(scan)
    except Exception as exc:
        scan.summary = f"Worker dispatch unavailable; scan remains queued. Reason: {exc}"
        db.add(
            AuditEvent(
                user_id=current_user.id,
                target_id=target.id,
                scan_id=scan.id,
                event_type="scan.dispatch_deferred",
                message="Celery broker unavailable during dispatch",
                details={"reason": str(exc)},
            )
        )
        await db.commit()
        await db.refresh(scan)
    return {"scan": ScanRead.model_validate(scan), "target": TargetRead.model_validate(target)}


@router.get("/{scan_id}", response_model=ScanRead)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await load_scan_for_user(db, scan_id=scan_id, user=current_user)
    return ScanRead.model_validate(scan)


@router.get("/{scan_id}/findings", response_model=list[FindingRead])
async def get_scan_findings(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Scan)
        .options(selectinload(Scan.findings))
        .where(Scan.id == scan_id, scan_access_filter(current_user))
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return [FindingRead.model_validate(finding) for finding in scan.findings]


@router.post("/{scan_id}/cancel", response_model=ScanRead)
async def cancel_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await load_scan_for_user(db, scan_id=scan_id, user=current_user, min_role="analyst")
    if scan.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Completed scans cannot be cancelled"
        )

    scan.status = "cancelled"
    scan.completed_at = datetime.now(timezone.utc)
    scan.summary = "Scan cancelled by user request."
    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=scan.target_id,
            scan_id=scan.id,
            event_type="scan.cancelled",
            message="Scan cancelled by API request",
            details=None,
        )
    )
    await db.commit()
    return ScanRead.model_validate(scan)


@router.post("/{scan_id}/pause", response_model=ScanRead)
async def pause_scan(
    scan_id: str,
    payload: ScanLifecycleRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await load_scan_for_user(db, scan_id=scan_id, user=current_user, min_role="analyst")
    if scan.status not in {"queued", "planning", "executing", "observing", "reflecting"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active scans can be paused")
    scan.status = "paused"
    scan.summary = payload.reason if payload and payload.reason else "Scan paused by user request."
    await db.commit()
    await db.refresh(scan)
    return ScanRead.model_validate(scan)


@router.post("/{scan_id}/resume", response_model=ScanRead)
async def resume_scan(
    scan_id: str,
    payload: ScanLifecycleRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await load_scan_for_user(db, scan_id=scan_id, user=current_user, min_role="analyst")
    if scan.status != "paused":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only paused scans can be resumed")
    scan.status = "queued"
    scan.summary = payload.reason if payload and payload.reason else "Scan resumed and queued for dispatch."
    await db.commit()
    await db.refresh(scan)
    return ScanRead.model_validate(scan)


@router.post("/{scan_id}/duplicate", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
async def duplicate_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = await load_scan_for_user(db, scan_id=scan_id, user=current_user, min_role="analyst")
    duplicate = Scan(
        target_id=source.target_id,
        organization_id=source.organization_id,
        requested_by_id=current_user.id,
        scan_profile_id=source.scan_profile_id,
        parent_scan_id=source.id,
        scan_type=source.scan_type,
        status="queued",
        scope=source.scope,
        started_at=datetime.now(timezone.utc),
        summary=f"Duplicated from scan {source.id}.",
        agent_trace=[],
        report_json=None,
    )
    db.add(duplicate)
    await db.flush()
    try:
        task = run_scan.delay(
            scan_id=duplicate.id,
            target_url=source.target.target_url if source.target else "",
            scan_type=duplicate.scan_type,
        )
        duplicate.celery_task_id = task.id
    except Exception as exc:
        duplicate.summary = f"Duplicated scan queued, but worker dispatch is unavailable: {exc}"
    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=duplicate.target_id,
            scan_id=duplicate.id,
            event_type="scan.duplicated",
            message=f"Scan duplicated from {source.id}.",
            details={"source_scan_id": source.id, "celery_task_id": duplicate.celery_task_id},
        )
    )
    await db.commit()
    await db.refresh(duplicate)
    return ScanRead.model_validate(duplicate)


@router.post("/{scan_id}/retry", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
async def retry_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await duplicate_scan(scan_id=scan_id, db=db, current_user=current_user)


@router.get("/{scan_id}/artifacts", response_model=list[ScanArtifactRead])
async def list_scan_artifacts(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await load_scan_for_user(db, scan_id=scan_id, user=current_user)
    result = await db.execute(
        select(ScanArtifact).where(ScanArtifact.scan_id == scan_id).order_by(ScanArtifact.created_at.desc())
    )
    return [ScanArtifactRead.model_validate(artifact) for artifact in result.scalars().all()]


@router.post("/{scan_id}/artifacts", response_model=ScanArtifactRead, status_code=status.HTTP_201_CREATED)
async def create_scan_artifact(
    scan_id: str,
    payload: ScanArtifactCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await load_scan_for_user(db, scan_id=scan_id, user=current_user, min_role="analyst")
    artifact = ScanArtifact(
        scan_id=scan_id,
        artifact_type=payload.artifact_type,
        name=payload.name,
        uri=payload.uri,
        content_type=payload.content_type,
        metadata_json=payload.metadata_json,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return ScanArtifactRead.model_validate(artifact)
