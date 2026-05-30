from __future__ import annotations

import json
from typing import Any

import httpx

from armorscan.config import settings


class GroqResponsesClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.groq_api_key)

    def _extract_json_payload(self, body: dict[str, Any]) -> dict[str, Any] | None:
        text = body.get("output_text")
        if not text:
            output = body.get("output") or []
            chunks: list[str] = []
            for item in output:
                for content in item.get("content") or []:
                    if isinstance(content, dict):
                        chunk = content.get("text") or content.get("output_text") or content.get("value")
                        if chunk:
                            chunks.append(str(chunk))
            text = "".join(chunks).strip() or None

        if not text:
            return None

        if isinstance(text, str):
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].lstrip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                start_candidates = [index for index in (cleaned.find("{"), cleaned.find("[")) if index >= 0]
                end_candidates = [cleaned.rfind("}"), cleaned.rfind("]")]
                if not start_candidates or max(end_candidates) < 0:
                    return None
                start = min(start_candidates)
                end = max(end_candidates)
                if end <= start:
                    return None
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    return None
        return None

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
                parsed = self._extract_json_payload(body)
                if parsed is not None:
                    return parsed
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {404, 422}:
                    raise
        try:
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
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            body = response.json()
            text = (body.get("choices") or [{}])[0].get("message", {}).get("content")
            if not text:
                return None
            return self._extract_json_payload({"output_text": text})
        except httpx.HTTPStatusError:
            return None
