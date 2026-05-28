from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


def scan_channel(scan_id: str) -> str:
    return f"scan:{scan_id}:events"


async def publish_scan_event(scan_id: str, payload: dict[str, Any]) -> bool:
    redis = None
    try:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis.publish(scan_channel(scan_id), json.dumps(payload, default=str))
        return True
    except Exception as exc:
        logger.debug("Failed to publish scan event for %s: %s", scan_id, exc)
        return False
    finally:
        if redis is not None:
            await redis.aclose()
