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
            try:
                response = await client.post("/responses", json=payload)
                response.raise_for_status()
                body = response.json()
                text = body.get("output_text")
                if text:
                    return json.loads(text)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {400, 404, 422}:
                    raise

            response = await client.post(
                "/chat/completions",
                json={
                    "model": settings.groq_model,
                    "messages": [
                        {"role": "system", "content": instructions},
                        {
                            "role": "user",
                            "content": (
                                f"{input_text}\n\nReturn only JSON that matches this schema:\n"
                                f"{json.dumps(json_schema['schema'], separators=(',', ':'))}"
                            ),
                        },
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            body = response.json()
            text = (body.get("choices") or [{}])[0].get("message", {}).get("content")
            if not text:
                return None
            return json.loads(text)
