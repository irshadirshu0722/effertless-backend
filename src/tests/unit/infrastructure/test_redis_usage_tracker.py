"""Unit tests for RedisUsageTracker."""

from datetime import UTC, datetime

import pytest

from app.adapters.redis_usage_tracker import RedisUsageTracker


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        val = self.store.get(key)
        return str(val) if val is not None else None

    async def incr(self, key: str) -> int:
        count = self.store.get(key, 0) + 1
        self.store[key] = count
        return count

    async def expire(self, key: str, ttl: int) -> None:
        self.expirations[key] = ttl


@pytest.mark.asyncio
async def test_redis_usage_tracker_get_and_increment() -> None:
    fake_redis = FakeRedis()
    tracker = RedisUsageTracker(fake_redis, ttl_seconds=86400)  # type: ignore[arg-type]

    # Initial usage should be 0
    assert await tracker.get_today_usage("usr-123") == 0

    # First increment should set TTL
    first_count = await tracker.increment_today_usage("usr-123")
    assert first_count == 1
    assert await tracker.get_today_usage("usr-123") == 1

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"usage:usr-123:{today}"
    assert fake_redis.expirations.get(key) == 86400

    # Subsequent increment
    second_count = await tracker.increment_today_usage("usr-123")
    assert second_count == 2
    assert await tracker.get_today_usage("usr-123") == 2
