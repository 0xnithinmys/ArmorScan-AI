from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=255)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    created_by_id: str | None
    created_at: datetime


class MembershipCreateRequest(BaseModel):
    user_email: EmailStr
    role: Literal["owner", "admin", "analyst", "viewer"] = "viewer"


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str
    role: str
    created_at: datetime


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=255)


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    slug: str
    created_at: datetime


class TargetCreateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    organization_id: str | None = None
    target_type: Literal["url", "github", "api"] = "url"
    target_url: str = Field(min_length=3)
    scope: list[str] = Field(default_factory=list)
    authorization_attestation: bool = False


class TargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None
    name: str
    target_type: str
    target_url: str
    scope: list[str]
    authorization_status: str
    authorization_proof_type: str | None
    authorization_verified_at: datetime | None = None
    created_at: datetime


class AuthorizationChallengeRequest(BaseModel):
    proof_type: Literal["dns_txt", "http_file", "meta_tag", "github_file"]


class AuthorizationProofRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_id: str
    created_by_id: str | None
    proof_type: str
    status: str
    challenge_token: str
    verification_target: str
    expected_value: str
    submitted_value: str | None
    instructions: str | None
    metadata_json: dict
    failure_reason: str | None
    last_checked_at: datetime | None
    verified_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class TargetAuthorizeRequest(BaseModel):
    proof_type: Literal["manual_attestation", "dns_txt", "http_file", "meta_tag", "github_file"] = (
        "manual_attestation"
    )
    proof: str | None = Field(default=None, min_length=8)
    challenge_token: str | None = Field(default=None, min_length=12)


class ScanCreateRequest(BaseModel):
    target_id: str | None = None
    target_url: str | None = None
    target_name: str | None = None
    organization_id: str | None = None
    scan_profile_id: str | None = None
    scan_type: Literal["url", "github", "api"] = "url"
    scope: list[str] = Field(default_factory=list)
    authorization_attestation: bool = False


class ScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_id: str
    organization_id: str | None
    requested_by_id: str
    scan_profile_id: str | None
    parent_scan_id: str | None
    scan_type: str
    status: str
    scope: list[str]
    celery_task_id: str | None
    summary: str | None
    agent_trace: list[dict]
    report_json: dict | None
    armoriq_token: str | None
    intent_plan: dict | None
    policy_decisions: list[dict]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ScanCreateResponse(BaseModel):
    scan: ScanRead
    target: TargetRead


class ScanLifecycleRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ScanProfileCreateRequest(BaseModel):
    organization_id: str | None = None
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    scan_type: Literal["url", "github", "api"] = "url"
    policy_tier: Literal["passive", "safe_active", "advanced_validated"] = "passive"
    settings_json: dict = Field(default_factory=dict)
    is_default: bool = False


class ScanProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None
    created_by_id: str | None
    name: str
    description: str | None
    scan_type: str
    policy_tier: str
    settings_json: dict
    is_default: bool
    created_at: datetime


class ScanArtifactCreateRequest(BaseModel):
    artifact_type: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    uri: str | None = None
    content_type: str | None = None
    metadata_json: dict = Field(default_factory=dict)


class ScanArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    artifact_type: str
    name: str
    uri: str | None
    content_type: str | None
    metadata_json: dict
    created_at: datetime


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    severity: str
    title: str
    location: str
    confidence: int
    risk_score: int
    risk_rating: str
    status: str
    summary: str
    business_impact: str | None
    remediation: str | None
    risk_factors: dict
    reproduction_steps: list[str]
    created_at: datetime


class FindingEvidenceCreateRequest(BaseModel):
    evidence_type: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    content: str | None = None
    artifact_uri: str | None = None
    metadata_json: dict = Field(default_factory=dict)


class FindingEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    evidence_type: str
    title: str
    content: str | None
    artifact_uri: str | None
    metadata_json: dict
    created_by_id: str | None
    created_at: datetime


class FindingCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1)


class FindingCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    author_id: str | None
    body: str
    created_at: datetime


class FindingSuppressionCreateRequest(BaseModel):
    reason: str = Field(min_length=3)
    expires_at: datetime | None = None


class FindingSuppressionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    created_by_id: str | None
    reason: str
    status: str
    expires_at: datetime | None
    created_at: datetime


class RemediationHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    actor_id: str | None
    from_status: str | None
    to_status: str
    note: str | None
    metadata_json: dict
    created_at: datetime


class FindingDetailRead(FindingRead):
    evidence: list[FindingEvidenceRead] = Field(default_factory=list)
    comments: list[FindingCommentRead] = Field(default_factory=list)
    suppressions: list[FindingSuppressionRead] = Field(default_factory=list)
    remediation_history: list[RemediationHistoryRead] = Field(default_factory=list)


class FindingStatusUpdate(BaseModel):
    status: Literal["open", "triaged", "resolved", "ignored"]
    note: str | None = None


class BulkFindingStatusUpdate(BaseModel):
    finding_ids: list[str] = Field(min_length=1)
    status: Literal["open", "triaged", "resolved", "ignored"]
    note: str | None = None


class CredentialReferenceCreateRequest(BaseModel):
    organization_id: str | None = None
    name: str = Field(min_length=2, max_length=255)
    credential_type: str = Field(min_length=2, max_length=64)
    vault_provider: str = Field(default="external", max_length=64)
    vault_reference: str = Field(min_length=3)
    metadata_json: dict = Field(default_factory=dict)


class CredentialReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None
    created_by_id: str | None
    name: str
    credential_type: str
    vault_provider: str
    vault_reference: str
    metadata_json: dict
    created_at: datetime


class WebhookIntegrationCreateRequest(BaseModel):
    organization_id: str | None = None
    name: str = Field(min_length=2, max_length=255)
    event_types: list[str] = Field(default_factory=list)
    target_url: str = Field(min_length=8)
    secret_reference: str | None = None
    is_active: bool = True


class WebhookIntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None
    created_by_id: str | None
    name: str
    event_types: list[str]
    target_url: str
    secret_reference: str | None
    is_active: bool
    created_at: datetime


class ReportExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    requested_by_id: str | None
    export_type: str
    status: str
    artifact_uri: str | None
    metadata_json: dict
    created_at: datetime


class ToolInventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    version: str | None
    status: str
    capabilities: list[str]
    last_checked_at: datetime | None
    metadata_json: dict
    created_at: datetime


class ToolInventoryUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=2, max_length=64)
    version: str | None = None
    status: Literal["available", "missing", "unknown", "disabled"] = "unknown"
    capabilities: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=dict)


class AgentExecutionLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str | None
    agent_name: str
    stage: str
    status: str
    message: str | None
    duration_ms: int | None
    metadata_json: dict
    created_at: datetime


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    target_id: str | None
    scan_id: str | None
    event_type: str
    message: str
    details: dict | None
    created_at: datetime
