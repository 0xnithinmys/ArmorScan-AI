import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.models import Scan, User
from app.services.event_bus import scan_channel
from app.services.access_control import load_scan_for_user

router = APIRouter()


@router.websocket("/scans/{scan_id}/stream")
async def scan_stream(websocket: WebSocket, scan_id: str, token: str | None = None):
    await websocket.accept()
    if not await _websocket_can_access_scan(scan_id, token):
        await websocket.send_text(json.dumps({"scan_id": scan_id, "status": "unauthorized"}))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    redis = None
    try:
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = redis.pubsub()
            await pubsub.subscribe(scan_channel(scan_id))

            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if message and message.get("data"):
                    await websocket.send_text(message["data"])
                    payload = json.loads(message["data"])
                    if payload.get("status") in {"completed", "failed", "cancelled"}:
                        break
                await asyncio.sleep(1)
        except Exception:
            last_trace_len = -1
            while True:
                async with AsyncSessionLocal() as session:
                    scan = await session.get(Scan, scan_id)
                    if scan is None:
                        await websocket.send_text(json.dumps({"scan_id": scan_id, "status": "missing"}))
                        break

                    if len(scan.agent_trace) != last_trace_len:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "scan_id": scan_id,
                                    "status": scan.status,
                                    "agent_trace": scan.agent_trace,
                                    "report_ready": bool(scan.report_json),
                                },
                                default=str,
                            )
                        )
                        last_trace_len = len(scan.agent_trace)

                    if scan.status in {"completed", "failed", "cancelled"}:
                        break
                await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    finally:
        if redis is not None:
            await redis.aclose()


async def _websocket_can_access_scan(scan_id: str, token: str | None) -> bool:
    if not token:
        return False
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return False
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == payload["sub"]))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return False
        try:
            await load_scan_for_user(session, scan_id=scan_id, user=user)
        except Exception:
            return False
        return True
