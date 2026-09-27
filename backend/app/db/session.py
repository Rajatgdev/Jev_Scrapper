"""Async SQLAlchemy engine on the POOLED Neon URL, for the app to query with.

Migrations use the DIRECT url (see migrate.py); the app uses the pooled one.
Small pool + pre-ping so a connection isn't reused stale after Neon compute
scales to zero (Neon serverless guidance).
"""
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings


def _async_url(url: str) -> str:
    """Neon hands out plain postgresql:// URLs with a libpq ?sslmode= param.
    The async engine needs the asyncpg driver, and asyncpg doesn't understand
    sslmode in the URL — so normalize the scheme and strip sslmode (asyncpg
    still negotiates SSL with Neon automatically)."""
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    for old, new in (("postgresql+asyncpg://", "postgresql+asyncpg://"),
                     ("postgresql://", "postgresql+asyncpg://"),
                     ("postgres://", "postgresql+asyncpg://")):
        if url.startswith(old):
            url = url.replace(old, new, 1)
            break

    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "sslmode"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode(query), parts.fragment))


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