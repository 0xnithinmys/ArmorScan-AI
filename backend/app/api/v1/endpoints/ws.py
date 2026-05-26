import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import Scan
from app.services.event_bus import scan_channel

router = APIRouter()


@router.websocket("/scans/{scan_id}/stream")
async def scan_stream(websocket: WebSocket, scan_id: str):
    await websocket.accept()
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
