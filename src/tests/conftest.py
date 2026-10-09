"""Global test fixtures and Testcontainers configuration."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

from app.api.dependencies import (
    get_db_session,
    get_identity_verifier,
    get_redis_client,
    get_settings,
)
from app.core.config import Settings
from app.core.exceptions import InvalidAuthTokenError
from app.domain.entities.authenticated_user import AuthenticatedUser
from app.drivers.models import Base
from app.ports.authentication import IdentityVerifier
from main import app as global_app
from main import create_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client():
    """Async test client for standard FastAPI application."""
    transport = ASGITransport(app=global_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# Testcontainers for PostgreSQL and Redis
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def postgres_container():
    """Spin up a real PostgreSQL container for integration testing."""
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def redis_container():
    """Spin up a real Redis container for integration testing."""
    container = RedisContainer("redis:7-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def postgres_url(postgres_container) -> str:
    """Return async SQLAlchemy connection string for the PostgreSQL container."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    password = postgres_container.password
    dbname = postgres_container.dbname
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"


@pytest.fixture(scope="session")
def redis_url(redis_container) -> str:
    """Return connection URL for the Redis container."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


@pytest.fixture(scope="session")
def init_db(postgres_url):
    """Create all database schema tables once per test session."""

    async def _init():
        engine = create_async_engine(postgres_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_init())


@pytest.fixture
async def clean_db(postgres_url, init_db):
    """Truncate all application tables before each integration test."""
    engine = create_async_engine(postgres_url)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("TRUNCATE TABLE subscription_webhook_events, subscriptions, plans CASCADE")
        )
    await engine.dispose()


@pytest.fixture
async def clean_redis(redis_url):
    """Flush all keys in Redis before each integration test."""
    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    await client.aclose()


@pytest.fixture
async def db_engine(postgres_url, init_db) -> AsyncGenerator[AsyncEngine, None]:
    """Provide an async engine connected to the container."""
    engine = create_async_engine(postgres_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine, clean_db) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session connected to the real container."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def redis_client(redis_url, clean_redis) -> AsyncGenerator[Redis, None]:
    """Provide an active Redis client connected to the real container."""
    client = Redis.from_url(redis_url, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def test_settings(
    postgres_url,
    redis_url,
    postgres_container,
    redis_container,
) -> Settings:
    """Settings configured with real testcontainer endpoints."""
    return Settings(
        database_url=postgres_url,
        postgres_host=postgres_container.get_container_host_ip(),
        postgres_port=int(postgres_container.get_exposed_port(5432)),
        redis_url=redis_url,
        redis_host=redis_container.get_container_host_ip(),
        redis_port=int(redis_container.get_exposed_port(6379)),
        cashfree_app_id="test_app_id",
        cashfree_secret_key="test_secret_key",
        cashfree_webhook_secret="test_webhook_secret",
        free_tier_days=7,
        free_tier_max_seconds=10,
        free_tier_max_requests_per_day=10,
    )


class TestIdentityVerifier(IdentityVerifier):
    """Verifier for integration tests allowing custom user IDs via token."""

    async def verify_token(self, token: str) -> AuthenticatedUser:
        if token.startswith("user:"):
            user_id = token.split("user:", 1)[1]
            return AuthenticatedUser(user_id=user_id, email=f"{user_id}@example.com")
        if token == "valid-token":
            return AuthenticatedUser(user_id="user-default", email="default@example.com")
        raise InvalidAuthTokenError()


@pytest.fixture
def integration_app(test_settings, postgres_url, redis_url, init_db):
    """FastAPI application wired to real testcontainers."""
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: test_settings

    engine = create_async_engine(postgres_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_db_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    redis = Redis.from_url(redis_url, decode_responses=True)

    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_redis_client] = lambda: redis
    app.dependency_overrides[get_identity_verifier] = lambda: TestIdentityVerifier()

    return app


@pytest.fixture
async def integration_client(
    integration_app, clean_db, clean_redis
) -> AsyncGenerator[AsyncClient, None]:
    """Async test client hitting the testcontainer-backed application."""
    transport = ASGITransport(app=integration_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
