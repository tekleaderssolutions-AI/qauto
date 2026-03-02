from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.config import get_settings


@lru_cache
def get_async_engine():
    settings = get_settings()
    url = settings.database_url or ""
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if not url:
        raise RuntimeError("DATABASE_URL must be set for async engine.")
    return create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=300,
    )


@lru_cache
def get_session_factory() -> sessionmaker:
    engine = get_async_engine()
    return sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session

