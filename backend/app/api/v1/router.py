from fastapi import APIRouter
from app.api.v1.endpoints import audit, auth, findings, organizations, platform, reports, scans, targets, ws

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(targets.router, prefix="/targets", tags=["targets"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(findings.router, prefix="/findings", tags=["findings"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(platform.router, prefix="/platform", tags=["platform"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
