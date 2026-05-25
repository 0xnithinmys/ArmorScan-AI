from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_findings():
    return {"findings": [], "message": "Findings — implemented in Phase 3"}


@router.patch("/{finding_id}/status")
async def update_finding_status(finding_id: str):
    return {"finding_id": finding_id, "message": "Status update — implemented in Phase 3"}
