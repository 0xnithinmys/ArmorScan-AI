from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from urllib.parse import urlparse

from app.api.deps import get_current_user
from app.api.v1.schemas import (
    AuthorizationChallengeRequest,
    AuthorizationProofRead,
    TargetAuthorizeRequest,
    TargetCreateRequest,
    TargetRead,
)
from app.core.database import get_db
from app.models import AuditEvent, Target, TargetAuthorizationProof, User
from app.services.access_control import load_target_for_user, require_org_role, target_access_filter
from app.services.target_authorization import (
    VERIFIED_PROOF_TYPES,
    create_proof_challenge,
    verify_proof,
)

router = APIRouter()


def _target_name_from_url(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host_or_path = parsed.hostname or parsed.path.strip("/\\") or "target"
    return host_or_path[:255]


async def _load_target_with_proofs(db: AsyncSession, *, target_id: str, user: User, min_role: str = "viewer") -> Target:
    return await load_target_for_user(db, target_id=target_id, user=user, min_role=min_role)


@router.get("/", response_model=list[TargetRead])
async def list_targets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Target)
        .options(selectinload(Target.authorization_proofs))
        .where(target_access_filter(current_user))
        .order_by(Target.created_at.desc())
    )
    return [TargetRead.model_validate(target) for target in result.scalars().all()]


@router.post("/", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
async def create_target(
    payload: TargetCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_org_role(db, organization_id=payload.organization_id, user=current_user, role="analyst")
    target = Target(
        owner_id=current_user.id,
        organization_id=payload.organization_id,
        name=(payload.name or "").strip() or _target_name_from_url(payload.target_url),
        target_type=payload.target_type,
        target_url=payload.target_url,
        scope=payload.scope,
        authorization_status="attested" if payload.authorization_attestation else "pending",
        authorization_proof_type="manual_attestation" if payload.authorization_attestation else None,
        authorization_proof="User attested authorization during target creation"
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
    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=target.id,
            event_type="target.created",
            message=f"Target {target.target_url} created.",
            details={
                "target_type": target.target_type,
                "authorization_status": target.authorization_status,
                "scope": target.scope,
            },
        )
    )
    await db.commit()
    target = await _load_target_with_proofs(db, target_id=target.id, user=current_user)
    return TargetRead.model_validate(target)


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = await _load_target_with_proofs(db, target_id=target_id, user=current_user, min_role="admin")

    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=target.id,
            event_type="target.deleted",
            message=f"Target {target.target_url} deleted.",
            details={"target_id": target.id},
        )
    )
    await db.delete(target)
    await db.commit()


@router.get("/{target_id}/proofs", response_model=list[AuthorizationProofRead])
async def list_target_proofs(
    target_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = await _load_target_with_proofs(db, target_id=target_id, user=current_user)
    proofs = sorted(target.authorization_proofs, key=lambda item: item.created_at, reverse=True)
    return [AuthorizationProofRead.model_validate(proof) for proof in proofs]


@router.post(
    "/{target_id}/proofs/challenge",
    response_model=AuthorizationProofRead,
    status_code=status.HTTP_201_CREATED,
)
async def issue_target_proof_challenge(
    target_id: str,
    payload: AuthorizationChallengeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = await _load_target_with_proofs(db, target_id=target_id, user=current_user, min_role="analyst")

    try:
        proof = create_proof_challenge(target=target, user=current_user, proof_type=payload.proof_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    db.add(proof)
    await db.flush()
    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=target.id,
            event_type="target.authorization_challenge_issued",
            message=f"Authorization challenge issued for {target.target_url}.",
            details={
                "proof_id": proof.id,
                "proof_type": proof.proof_type,
                "verification_target": proof.verification_target,
                "expires_at": proof.expires_at.isoformat() if proof.expires_at else None,
            },
        )
    )
    await db.commit()
    await db.refresh(proof)
    return AuthorizationProofRead.model_validate(proof)


@router.post("/{target_id}/authorize", response_model=TargetRead)
async def authorize_target(
    target_id: str,
    payload: TargetAuthorizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = await _load_target_with_proofs(db, target_id=target_id, user=current_user, min_role="analyst")

    if payload.proof_type == "manual_attestation":
        proof = create_proof_challenge(target=target, user=current_user, proof_type="manual_attestation")
        db.add(proof)
    else:
        proof_query = (
            select(TargetAuthorizationProof)
            .where(
                TargetAuthorizationProof.target_id == target.id,
                TargetAuthorizationProof.proof_type == payload.proof_type,
            )
            .order_by(TargetAuthorizationProof.created_at.desc())
        )
        if payload.challenge_token:
            proof_query = proof_query.where(
                TargetAuthorizationProof.challenge_token == payload.challenge_token
            )
        proof_result = await db.execute(proof_query.limit(1))
        proof = proof_result.scalar_one_or_none()
        if proof is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No pending authorization challenge found for this proof type. Issue a challenge first.",
            )

    previous_status = target.authorization_status
    previous_proof_type = target.authorization_proof_type
    previous_proof = target.authorization_proof

    result = await verify_proof(target=target, proof=proof, submitted_value=payload.proof)
    proof.submitted_value = result.submitted_value
    proof.failure_reason = None if result.ok else result.message
    proof.last_checked_at = datetime.now(timezone.utc)
    proof.status = result.status
    if result.ok and result.status in {"verified", "attested"}:
        proof.verified_at = datetime.now(timezone.utc)

    if result.ok and proof.proof_type in VERIFIED_PROOF_TYPES:
        target.authorization_status = "verified"
        target.authorization_proof_type = proof.proof_type
        target.authorization_proof = proof.submitted_value or proof.verification_target
    elif result.ok:
        target.authorization_status = "attested"
        target.authorization_proof_type = proof.proof_type
        target.authorization_proof = proof.submitted_value
    else:
        target.authorization_status = previous_status
        target.authorization_proof_type = previous_proof_type
        target.authorization_proof = previous_proof

    await db.flush()
    db.add(
        AuditEvent(
            user_id=current_user.id,
            target_id=target.id,
            event_type="target.authorized" if result.ok else "target.authorization_failed",
            message=result.message,
            details={
                "proof_type": payload.proof_type,
                "proof_id": proof.id,
                "status": proof.status,
            },
        )
    )
    await db.commit()
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.message)
    target = await _load_target_with_proofs(db, target_id=target.id, user=current_user)
    return TargetRead.model_validate(target)
