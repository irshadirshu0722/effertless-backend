"""Redis-backed usage tracker for atomic daily quota enforcement."""

from datetime import UTC, datetime

from redis.asyncio import Redis

from app.ports.subscription import UsageTracker


class RedisUsageTracker(UsageTracker):
    """Tracks daily user request counts using Redis with automatic TTL."""

    def __init__(self, redis: Redis, ttl_seconds: int = 172800) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _usage_key(user_id: str, now: datetime | None = None) -> str:
        current_time = now or datetime.now(UTC)
        date_str = current_time.strftime("%Y-%m-%d")
        return f"usage:{user_id}:{date_str}"

    async def get_today_usage(self, user_id: str) -> int:
        key = self._usage_key(user_id)
        value = await self._redis.get(key)
        if value is None:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    async def increment_today_usage(self, user_id: str) -> int:
        key = self._usage_key(user_id)
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, self._ttl_seconds)
        return count
