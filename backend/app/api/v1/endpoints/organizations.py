from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.schemas import (
    MembershipCreateRequest,
    MembershipRead,
    OrganizationCreateRequest,
    OrganizationRead,
    TeamCreateRequest,
    TeamRead,
)
from app.core.database import get_db
from app.models import AuditEvent, Membership, Organization, Team, User
from app.services.access_control import assert_allowed_role, require_org_role, slugify

router = APIRouter()


@router.get("/", response_model=list[OrganizationRead])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Organization)
        .join(Membership)
        .where(Membership.user_id == current_user.id)
        .order_by(Organization.created_at.desc())
    )
    return [OrganizationRead.model_validate(org) for org in result.scalars().all()]


@router.post("/", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_slug = slugify(payload.slug or payload.name)
    slug = base_slug
    suffix = 2
    while True:
        existing = await db.execute(select(Organization).where(Organization.slug == slug))
        if existing.scalar_one_or_none() is None:
            break
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    org = Organization(name=payload.name.strip(), slug=slug, created_by_id=current_user.id)
    db.add(org)
    await db.flush()
    db.add(Membership(organization_id=org.id, user_id=current_user.id, role="owner"))
    db.add(
        AuditEvent(
            user_id=current_user.id,
            event_type="organization.created",
            message=f"Organization {org.name} created.",
            details={"organization_id": org.id, "slug": org.slug},
        )
    )
    await db.commit()
    await db.refresh(org)
    return OrganizationRead.model_validate(org)


@router.get("/{organization_id}/members", response_model=list[MembershipRead])
async def list_members(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_org_role(db, organization_id=organization_id, user=current_user, role="viewer")
    result = await db.execute(
        select(Membership)
        .where(Membership.organization_id == organization_id)
        .order_by(Membership.created_at.asc())
    )
    return [MembershipRead.model_validate(member) for member in result.scalars().all()]


@router.post("/{organization_id}/members", response_model=MembershipRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    organization_id: str,
    payload: MembershipCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_allowed_role(payload.role)
    await require_org_role(db, organization_id=organization_id, user=current_user, role="admin")

    user_result = await db.execute(select(User).where(User.email == payload.user_email))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        membership = Membership(organization_id=organization_id, user_id=user.id, role=payload.role)
        db.add(membership)
    else:
        membership.role = payload.role

    db.add(
        AuditEvent(
            user_id=current_user.id,
            event_type="organization.member_upserted",
            message=f"Member {user.email} set to {payload.role}.",
            details={"organization_id": organization_id, "member_user_id": user.id, "role": payload.role},
        )
    )
    await db.commit()
    await db.refresh(membership)
    return MembershipRead.model_validate(membership)


@router.get("/{organization_id}/teams", response_model=list[TeamRead])
async def list_teams(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_org_role(db, organization_id=organization_id, user=current_user, role="viewer")
    result = await db.execute(
        select(Team).where(Team.organization_id == organization_id).order_by(Team.created_at.desc())
    )
    return [TeamRead.model_validate(team) for team in result.scalars().all()]


@router.post("/{organization_id}/teams", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
    organization_id: str,
    payload: TeamCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_org_role(db, organization_id=organization_id, user=current_user, role="admin")
    base_slug = slugify(payload.slug or payload.name)
    slug = base_slug
    suffix = 2
    while True:
        existing = await db.execute(
            select(Team).where(Team.organization_id == organization_id, Team.slug == slug)
        )
        if existing.scalar_one_or_none() is None:
            break
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    team = Team(organization_id=organization_id, name=payload.name.strip(), slug=slug)
    db.add(team)
    db.add(
        AuditEvent(
            user_id=current_user.id,
            event_type="organization.team_created",
            message=f"Team {team.name} created.",
            details={"organization_id": organization_id, "team_id": team.id, "slug": team.slug},
        )
    )
    await db.commit()
    await db.refresh(team)
    return TeamRead.model_validate(team)
