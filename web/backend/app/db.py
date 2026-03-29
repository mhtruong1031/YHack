from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def normalize_async_database_url(url: str) -> str:
    """Runtime async SQLAlchemy uses psycopg3 async (postgresql+psycopg_async://)."""
    u = url.strip()
    if u.startswith("postgresql+psycopg_async://"):
        return u
    if u.startswith("postgresql+asyncpg://"):
        rest = u[len("postgresql+asyncpg://") :]
        return f"postgresql+psycopg_async://{rest}"
    if u.startswith("postgresql://"):
        rest = u[len("postgresql://") :]
        return f"postgresql+psycopg_async://{rest}"
    if u.startswith("postgres://"):
        rest = u[len("postgres://") :]
        return f"postgresql+psycopg_async://{rest}"
    return u


def sync_database_url_for_alembic(url: str) -> str:
    """Alembic runs sync migrations; use psycopg3 sync driver."""
    u = url.strip()
    for prefix in (
        "postgresql+psycopg_async://",
        "postgresql+asyncpg://",
        "postgresql://",
        "postgres://",
    ):
        if u.startswith(prefix):
            rest = u[len(prefix) :]
            return f"postgresql+psycopg://{rest}"
    return u


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            normalize_async_database_url(get_settings().database_url),
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


__all__ = [
    "dispose_engine",
    "get_engine",
    "get_session",
    "get_session_factory",
    "normalize_async_database_url",
    "sync_database_url_for_alembic",
]
