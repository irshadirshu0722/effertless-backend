"""SQLAlchemy engine and session factory configuration."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create an async SQLAlchemy engine from environment-backed settings."""
    if not settings.database_url:
        raise ValueError("DATABASE_URL must be configured")
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create the application async session factory."""
    return async_sessionmaker(engine, expire_on_commit=False)
