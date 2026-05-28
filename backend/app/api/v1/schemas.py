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


class TargetCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    target_type: Literal["url", "github", "api"] = "url"
    target_url: str = Field(min_length=3)
    scope: list[str] = Field(default_factory=list)
    authorization_attestation: bool = False


class TargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    target_type: str
    target_url: str
    scope: list[str]
    authorization_status: str
    authorization_proof_type: str | None
    created_at: datetime


class TargetAuthorizeRequest(BaseModel):
    proof_type: Literal["manual_attestation", "dns_txt", "meta_tag"] = "manual_attestation"
    proof: str = Field(min_length=8)


class ScanCreateRequest(BaseModel):
    target_id: str | None = None
    target_url: str | None = None
    target_name: str | None = None
    scan_type: Literal["url", "github", "api"] = "url"
    scope: list[str] = Field(default_factory=list)
    authorization_attestation: bool = False


class ScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_id: str
    requested_by_id: str
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


class FindingStatusUpdate(BaseModel):
    status: Literal["open", "triaged", "resolved", "ignored"]


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
