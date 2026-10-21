"""Redis client factory."""

from redis.asyncio import Redis

from app.core.config import Settings


def create_redis_client(settings: Settings) -> Redis:
    """Create a Redis client from environment-backed settings."""
    return Redis.from_url(settings.redis_url, decode_responses=True)
