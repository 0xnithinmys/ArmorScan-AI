from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_audit_events():
    return {"events": [], "message": "Audit log — implemented in Phase 3"}
