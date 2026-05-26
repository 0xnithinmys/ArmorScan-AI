from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.schemas import TargetAuthorizeRequest, TargetCreateRequest, TargetRead
from app.core.database import get_db
from app.models import Target, User

router = APIRouter()


@router.get("/", response_model=list[TargetRead])
async def list_targets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Target).where(Target.owner_id == current_user.id).order_by(Target.created_at.desc())
    )
    return [TargetRead.model_validate(target) for target in result.scalars().all()]


@router.post("/", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
async def create_target(
    payload: TargetCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = Target(
        owner_id=current_user.id,
        name=payload.name,
        target_type=payload.target_type,
        target_url=payload.target_url,
        scope=payload.scope,
        authorization_status="verified" if payload.authorization_attestation else "pending",
        authorization_proof_type="manual_attestation" if payload.authorization_attestation else None,
        authorization_proof="User attested authorization during target creation"
        if payload.authorization_attestation
        else None,
    )
    db.add(target)
    await db.flush()
    return TargetRead.model_validate(target)


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Target).where(Target.id == target_id, Target.owner_id == current_user.id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    await db.delete(target)


@router.post("/{target_id}/authorize", response_model=TargetRead)
async def authorize_target(
    target_id: str,
    payload: TargetAuthorizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Target).where(Target.id == target_id, Target.owner_id == current_user.id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    if payload.proof_type == "manual_attestation" and payload.proof.strip() != "I_AM_AUTHORIZED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Manual attestation proof must be I_AM_AUTHORIZED",
        )

    target.authorization_status = "verified"
    target.authorization_proof_type = payload.proof_type
    target.authorization_proof = payload.proof
    await db.flush()
    return TargetRead.model_validate(target)
