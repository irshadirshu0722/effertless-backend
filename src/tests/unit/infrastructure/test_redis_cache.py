"""Tests for the Redis cache adapter."""

import pytest

from app.adapters.redis_cache import RedisCache


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        self.values[key] = value
        self.ttls[key] = ex

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)
        self.ttls.pop(key, None)


@pytest.mark.asyncio
async def test_redis_cache_round_trip() -> None:
    cache = RedisCache(FakeRedis())

    await cache.set("subscription:user-1", "active", ttl_seconds=60)
    assert await cache.get("subscription:user-1") == "active"

    await cache.delete("subscription:user-1")
    assert await cache.get("subscription:user-1") is None
