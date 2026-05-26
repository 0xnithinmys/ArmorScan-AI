from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.api.v1.schemas import FindingRead, ScanCreateRequest, ScanRead, TargetRead
from app.core.database import get_db
from app.models import AuditEvent, Scan, Target, User
from app.services.policy import (
    PolicyViolation,
    build_intent_plan,
    evaluate_scan_request,
    require_allowed,
    sign_intent_plan,
)
from app.workers.scan_worker import run_scan

router = APIRouter()


@router.get("/", response_model=list[ScanRead])
async def list_scans(
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Scan).where(Scan.requested_by_id == current_user.id).order_by(Scan.created_at.desc())
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
        result = await db.execute(
            select(Target).where(Target.id == payload.target_id, Target.owner_id == current_user.id)
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    elif payload.target_url and payload.target_name:
        target = Target(
            owner_id=current_user.id,
            name=payload.target_name,
            target_type=payload.scan_type,
            target_url=payload.target_url,
            scope=payload.scope,
            authorization_status="verified" if payload.authorization_attestation else "pending",
            authorization_proof_type="manual_attestation" if payload.authorization_attestation else None,
            authorization_proof="User attested authorization during scan creation"
            if payload.authorization_attestation
            else None,
        )
        db.add(target)
        await db.flush()
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either target_id or both target_url and target_name",
        )

    scan = Scan(
        target_id=target.id,
        requested_by_id=current_user.id,
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

    return {"scan": ScanRead.model_validate(scan), "target": TargetRead.model_validate(target)}


@router.get("/{scan_id}", response_model=ScanRead)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.requested_by_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
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
        .where(Scan.id == scan_id, Scan.requested_by_id == current_user.id)
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
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.requested_by_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
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
    return ScanRead.model_validate(scan)
