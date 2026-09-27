"""Async SQLAlchemy engine on the POOLED Neon URL, for the app to query with.

Migrations use the DIRECT url (see migrate.py); the app uses the pooled one.
Small pool + pre-ping so a connection isn't reused stale after Neon compute
scales to zero (Neon serverless guidance).
"""
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings


def _async_url(url: str) -> str:
    """Neon hands out plain postgresql:// URLs; the async engine needs the
    asyncpg driver. Normalize so either form pasted into .env works."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _async_url(settings.database_url),
    pool_size=2,
    max_overflow=0,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    """FastAPI dependency: one fresh AsyncSession per request."""
    async with SessionLocal() as session:
        yield session