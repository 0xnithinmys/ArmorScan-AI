from fastapi import APIRouter
from app.api.v1.endpoints import auth, targets, scans, findings, reports, audit, ws

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(targets.router, prefix="/targets", tags=["targets"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(findings.router, prefix="/findings", tags=["findings"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
