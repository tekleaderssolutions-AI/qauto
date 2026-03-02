from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db as _get_db


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Re-exported DB dependency for FastAPI routes."""
    async for session in _get_db():
        yield session

