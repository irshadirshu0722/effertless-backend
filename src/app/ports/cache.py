"""Application cache port."""

from typing import Protocol


class CachePort(Protocol):
    """Minimal async cache contract used by application services."""

    async def get(self, key: str) -> str | None:
        """Return a cached value, if present."""

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Store a value for a bounded period."""

    async def delete(self, key: str) -> None:
        """Delete a cached value."""
