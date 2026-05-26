from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings


def scan_channel(scan_id: str) -> str:
    return f"scan:{scan_id}:events"


async def publish_scan_event(scan_id: str, payload: dict[str, Any]) -> bool:
    try:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis.publish(scan_channel(scan_id), json.dumps(payload, default=str))
        await redis.aclose()
        return True
    except Exception:
        return False
