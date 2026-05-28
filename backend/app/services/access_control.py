from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Membership, Scan, Target, User


ROLE_RANK = {
    "viewer": 10,
    "analyst": 20,
    "admin": 30,
    "owner": 40,
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "workspace"


def role_allows(actual: str | None, required: str) -> bool:
    return ROLE_RANK.get(actual or "", 0) >= ROLE_RANK[required]


async def membership_for_user(
    db: AsyncSession, *, organization_id: str | None, user: User
) -> Membership | None:
    if not organization_id:
        return None
    result = await db.execute(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user.id,
        )
    )
    return result.scalar_one_or_none()


async def require_org_role(
    db: AsyncSession, *, organization_id: str | None, user: User, role: str
) -> Membership | None:
    if organization_id is None:
        return None
    membership = await membership_for_user(db, organization_id=organization_id, user=user)
    if membership is None or not role_allows(membership.role, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {role} access to this organization",
        )
    return membership


def target_access_filter(user: User):
    return or_(
        Target.owner_id == user.id,
        Target.organization_id.in_(
            select(Membership.organization_id).where(Membership.user_id == user.id)
        ),
    )


def scan_access_filter(user: User):
    return or_(
        Scan.requested_by_id == user.id,
        Scan.organization_id.in_(
            select(Membership.organization_id).where(Membership.user_id == user.id)
        ),
    )


async def load_target_for_user(
    db: AsyncSession, *, target_id: str, user: User, min_role: str = "viewer"
) -> Target:
    result = await db.execute(
        select(Target)
        .options(selectinload(Target.authorization_proofs))
        .where(Target.id == target_id, target_access_filter(user))
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    if target.owner_id != user.id:
        await require_org_role(db, organization_id=target.organization_id, user=user, role=min_role)
    return target


async def load_scan_for_user(
    db: AsyncSession, *, scan_id: str, user: User, min_role: str = "viewer"
) -> Scan:
    result = await db.execute(
        select(Scan)
        .options(selectinload(Scan.target), selectinload(Scan.findings))
        .where(Scan.id == scan_id, scan_access_filter(user))
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    if scan.requested_by_id != user.id:
        await require_org_role(db, organization_id=scan.organization_id, user=user, role=min_role)
    return scan


def assert_allowed_role(role: str) -> None:
    if role not in ROLE_RANK:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported role. Use one of: {', '.join(ROLE_RANK)}",
        )

