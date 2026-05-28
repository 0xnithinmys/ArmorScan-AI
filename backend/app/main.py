from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import models  # noqa: F401
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migrations own schema changes; startup only verifies connectivity.
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("[startup] Database connected.")
    except Exception as exc:
        print(f"[startup] WARNING: Could not connect to database: {exc}")
        print("[startup] Server will start anyway; DB-dependent endpoints may fail.")
    yield
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="ArmorScan AI",
    description="AI-native autonomous web security auditing platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "armorscan-api"}
