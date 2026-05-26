from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()
load_dotenv("../.env")


@dataclass(slots=True)
class AgentSettings:
    groq_api_key: str = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    groq_reasoning_effort: str = os.getenv("GROQ_REASONING_EFFORT", "medium")
    request_timeout_seconds: float = float(os.getenv("GROQ_TIMEOUT_SECONDS", "45"))


settings = AgentSettings()
