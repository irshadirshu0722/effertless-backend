from uuid import uuid4

import pytest
from redis.asyncio import Redis


@pytest.fixture
def cache_key() -> str:
    """Generate a unique key to prevent interference between tests."""
    return f"test:cache:{uuid4().hex}"


async def test_get_returns_none_for_missing_key(
    redis_cache,
    cache_key: str,
) -> None:
    result = await redis_cache.get(cache_key)

    assert result is None


async def test_set_and_get_returns_stored_value(
    redis_cache,
    cache_key: str,
) -> None:
    await redis_cache.set(cache_key, "hello", ttl_seconds=60)

    result = await redis_cache.get(cache_key)

    assert result == "hello"


async def test_set_stores_value_with_ttl(
    redis_cache,
    redis_client: Redis,
    cache_key: str,
) -> None:
    ttl_seconds = 60

    await redis_cache.set(
        cache_key,
        "temporary-value",
        ttl_seconds=ttl_seconds,
    )

    result = await redis_client.ttl(cache_key)

    assert 0 < result <= ttl_seconds


async def test_set_overwrites_existing_value(
    redis_cache,
    cache_key: str,
) -> None:
    await redis_cache.set(cache_key, "old-value", ttl_seconds=60)
    await redis_cache.set(cache_key, "new-value", ttl_seconds=120)

    result = await redis_cache.get(cache_key)

    assert result == "new-value"


async def test_delete_removes_existing_key(
    redis_cache,
    cache_key: str,
) -> None:
    await redis_cache.set(cache_key, "value", ttl_seconds=60)

    await redis_cache.delete(cache_key)

    result = await redis_cache.get(cache_key)

    assert result is None


async def test_delete_missing_key_does_not_raise(
    redis_cache,
    cache_key: str,
) -> None:
    await redis_cache.delete(cache_key)

    assert await redis_cache.get(cache_key) is None


async def test_cache_supports_empty_string(
    redis_cache,
    cache_key: str,
) -> None:
    await redis_cache.set(cache_key, "", ttl_seconds=60)

    result = await redis_cache.get(cache_key)

    assert result == ""


async def test_cache_supports_json_string(
    redis_cache,
    cache_key: str,
) -> None:
    value = '{"user_id": "user-123", "active": true}'

    await redis_cache.set(cache_key, value, ttl_seconds=60)

    result = await redis_cache.get(cache_key)

    assert result == value
