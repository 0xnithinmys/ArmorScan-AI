from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.schemas import AuditEventRead
from app.core.database import get_db
from app.models import AuditEvent, User

router = APIRouter()


@router.get("/", response_model=list[AuditEventRead])
async def list_audit_events(
    scan_id: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(AuditEvent)
        .where((AuditEvent.user_id == current_user.id) | (AuditEvent.user_id.is_(None)))
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    if scan_id:
        stmt = stmt.where(AuditEvent.scan_id == scan_id)
    if target_id:
        stmt = stmt.where(AuditEvent.target_id == target_id)

    result = await db.execute(stmt)
    return [AuditEventRead.model_validate(event) for event in result.scalars().all()]
