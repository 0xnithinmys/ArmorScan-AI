from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.schemas import (
    AgentExecutionLogRead,
    CredentialReferenceCreateRequest,
    CredentialReferenceRead,
    ScanProfileCreateRequest,
    ScanProfileRead,
    ToolInventoryRead,
    ToolInventoryUpsertRequest,
    WebhookIntegrationCreateRequest,
    WebhookIntegrationRead,
)
from app.core.database import get_db
from app.models import (
    AuditEvent,
    AgentExecutionLog,
    CredentialReference,
    Membership,
    ScanProfile,
    ToolInventory,
    User,
    WebhookIntegration,
)
from app.services.access_control import require_org_role

router = APIRouter()


def _org_scope(model, organization_id: str | None, current_user: User):
    if organization_id:
        return model.organization_id == organization_id
    return (model.organization_id.is_(None)) | (
        model.organization_id.in_(
            select(Membership.organization_id).where(Membership.user_id == current_user.id)
        )
    )


@router.get("/scan-profiles", response_model=list[ScanProfileRead])
async def list_scan_profiles(
    organization_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id:
        await require_org_role(db, organization_id=organization_id, user=current_user, role="viewer")
    result = await db.execute(
        select(ScanProfile)
        .where(_org_scope(ScanProfile, organization_id, current_user))
        .order_by(ScanProfile.created_at.desc())
    )
    return [ScanProfileRead.model_validate(profile) for profile in result.scalars().all()]


@router.post("/scan-profiles", response_model=ScanProfileRead, status_code=status.HTTP_201_CREATED)
async def create_scan_profile(
    payload: ScanProfileCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_org_role(db, organization_id=payload.organization_id, user=current_user, role="analyst")
    profile = ScanProfile(
        organization_id=payload.organization_id,
        created_by_id=current_user.id,
        name=payload.name,
        description=payload.description,
        scan_type=payload.scan_type,
        policy_tier=payload.policy_tier,
        settings_json=payload.settings_json,
        is_default=payload.is_default,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return ScanProfileRead.model_validate(profile)


@router.get("/credentials", response_model=list[CredentialReferenceRead])
async def list_credentials(
    organization_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id:
        await require_org_role(db, organization_id=organization_id, user=current_user, role="viewer")
    result = await db.execute(
        select(CredentialReference)
        .where(_org_scope(CredentialReference, organization_id, current_user))
        .order_by(CredentialReference.created_at.desc())
    )
    return [CredentialReferenceRead.model_validate(item) for item in result.scalars().all()]


@router.post("/credentials", response_model=CredentialReferenceRead, status_code=status.HTTP_201_CREATED)
async def create_credential(
    payload: CredentialReferenceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_org_role(db, organization_id=payload.organization_id, user=current_user, role="admin")
    credential = CredentialReference(
        organization_id=payload.organization_id,
        created_by_id=current_user.id,
        name=payload.name,
        credential_type=payload.credential_type,
        vault_provider=payload.vault_provider,
        vault_reference=payload.vault_reference,
        metadata_json=payload.metadata_json,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return CredentialReferenceRead.model_validate(credential)


@router.get("/webhooks", response_model=list[WebhookIntegrationRead])
async def list_webhooks(
    organization_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id:
        await require_org_role(db, organization_id=organization_id, user=current_user, role="viewer")
    result = await db.execute(
        select(WebhookIntegration)
        .where(_org_scope(WebhookIntegration, organization_id, current_user))
        .order_by(WebhookIntegration.created_at.desc())
    )
    return [WebhookIntegrationRead.model_validate(item) for item in result.scalars().all()]


@router.post("/webhooks", response_model=WebhookIntegrationRead, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    payload: WebhookIntegrationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_org_role(db, organization_id=payload.organization_id, user=current_user, role="admin")
    webhook = WebhookIntegration(
        organization_id=payload.organization_id,
        created_by_id=current_user.id,
        name=payload.name,
        event_types=payload.event_types,
        target_url=payload.target_url,
        secret_reference=payload.secret_reference,
        is_active=payload.is_active,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return WebhookIntegrationRead.model_validate(webhook)


@router.get("/tools", response_model=list[ToolInventoryRead])
async def list_tools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ToolInventory).order_by(ToolInventory.name.asc()))
    return [ToolInventoryRead.model_validate(tool) for tool in result.scalars().all()]


@router.put("/tools/{tool_name}", response_model=ToolInventoryRead)
async def upsert_tool(
    tool_name: str,
    payload: ToolInventoryUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ToolInventory).where(ToolInventory.name == tool_name))
    tool = result.scalar_one_or_none()
    if tool is None:
        tool = ToolInventory(name=tool_name, category=payload.category)
        db.add(tool)
    tool.name = payload.name or tool_name
    tool.category = payload.category
    tool.version = payload.version
    tool.status = payload.status
    tool.capabilities = payload.capabilities
    tool.metadata_json = payload.metadata_json
    db.add(
        AuditEvent(
            user_id=current_user.id,
            event_type="tool_inventory.upserted",
            message=f"Tool inventory updated for {tool.name}.",
            details={
                "name": tool.name,
                "category": tool.category,
                "status": tool.status,
                "capabilities": tool.capabilities,
            },
        )
    )
    await db.commit()
    await db.refresh(tool)
    return ToolInventoryRead.model_validate(tool)


@router.get("/agent-logs", response_model=list[AgentExecutionLogRead])
async def list_agent_logs(
    scan_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(AgentExecutionLog).order_by(AgentExecutionLog.created_at.desc()).limit(limit)
    if scan_id:
        from app.services.access_control import load_scan_for_user

        await load_scan_for_user(db, scan_id=scan_id, user=current_user, min_role="viewer")
        stmt = stmt.where(AgentExecutionLog.scan_id == scan_id)
    result = await db.execute(stmt)
    return [AgentExecutionLogRead.model_validate(log) for log in result.scalars().all()]
