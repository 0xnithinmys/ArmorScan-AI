import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from sqlalchemy.pool import NullPool

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
)

_sessionmakers_by_loop: dict[int, async_sessionmaker[AsyncSession]] = {}


def _create_sessionmaker() -> async_sessionmaker[AsyncSession]:
    loop_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
    )
    return async_sessionmaker(
        loop_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


class _LoopLocalSessionFactory:
    def __call__(self, **kwargs: Any) -> AsyncSession:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return _create_sessionmaker()(**kwargs)
        loop_id = id(loop)
        sessionmaker = _sessionmakers_by_loop.get(loop_id)
        if sessionmaker is None:
            sessionmaker = _create_sessionmaker()
            _sessionmakers_by_loop[loop_id] = sessionmaker
        return sessionmaker(**kwargs)


AsyncSessionLocal = _LoopLocalSessionFactory()


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
