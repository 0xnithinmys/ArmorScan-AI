from fastapi import APIRouter

router = APIRouter()


@router.get("/{scan_id}/pdf")
async def download_pdf(scan_id: str):
    return {"message": f"PDF report for {scan_id} — implemented in Phase 8"}


@router.get("/{scan_id}/sarif")
async def download_sarif(scan_id: str):
    return {"message": f"SARIF report for {scan_id} — implemented in Phase 8"}


@router.get("/{scan_id}/json")
async def download_json(scan_id: str):
    return {"message": f"JSON report for {scan_id} — implemented in Phase 8"}
