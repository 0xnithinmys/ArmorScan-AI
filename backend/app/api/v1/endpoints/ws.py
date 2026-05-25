from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio

router = APIRouter()


@router.websocket("/scans/{scan_id}/stream")
async def scan_stream(websocket: WebSocket, scan_id: str):
    """
    WebSocket endpoint — streams live agent trace events for a given scan.
    Phase 4 will push real events via Redis pub/sub into this connection.
    """
    await websocket.accept()
    try:
        # Placeholder: send a ping every 5s until real agent events are wired in Phase 4
        while True:
            await websocket.send_text(
                json.dumps({"type": "ping", "scan_id": scan_id, "message": "Connection alive"})
            )
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
