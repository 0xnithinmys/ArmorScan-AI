from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_targets():
    return {"targets": [], "message": "Target management — implemented in Phase 3"}


@router.post("/")
async def create_target():
    return {"message": "Create target — implemented in Phase 3"}


@router.delete("/{target_id}")
async def delete_target(target_id: str):
    return {"message": f"Delete target {target_id} — implemented in Phase 3"}
