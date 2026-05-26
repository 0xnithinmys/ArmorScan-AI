from __future__ import annotations

import json
from typing import Any

import httpx

from armorscan.config import settings


class GroqResponsesClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.groq_api_key)

    async def create_structured_response(
        self,
        *,
        instructions: str,
        input_text: str,
        json_schema: dict[str, Any],
        reasoning_effort: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        payload = {
            "model": settings.groq_model,
            "instructions": instructions,
            "input": input_text,
            "reasoning": {"effort": reasoning_effort or settings.groq_reasoning_effort},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": json_schema.get("name", "armorscan_schema"),
                    "schema": json_schema["schema"],
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            base_url=settings.groq_base_url,
            timeout=settings.request_timeout_seconds,
            headers=headers,
        ) as client:
            response = await client.post("/responses", json=payload)
            response.raise_for_status()
            body = response.json()
            text = body.get("output_text")
            if not text:
                return None
            return json.loads(text)
