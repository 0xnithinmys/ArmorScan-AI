from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

router = APIRouter()


class ScanRequest(BaseModel):
    target_url: str
    scan_type: Literal["url", "github", "api"] = "url"
    scope: list[str] = []


@router.post("/")
async def initiate_scan(payload: ScanRequest):
    # TODO: validate target, submit ArmorIQ intent, dispatch Celery task
    return {"scan_id": "placeholder-scan-id", "status": "queued", "target": payload.target_url}


@router.get("/{scan_id}")
async def get_scan(scan_id: str):
    return {"scan_id": scan_id, "status": "running", "message": "Full implementation in Phase 3"}


@router.get("/{scan_id}/findings")
async def get_scan_findings(scan_id: str):
    return {"scan_id": scan_id, "findings": []}


@router.post("/{scan_id}/cancel")
async def cancel_scan(scan_id: str):
    return {"scan_id": scan_id, "status": "cancelled"}
