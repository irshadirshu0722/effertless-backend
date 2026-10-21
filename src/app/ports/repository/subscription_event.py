"""Subscription, payment, and quota tracking ports."""

from typing import Any, Protocol


class WebhookEventRepository(Protocol):
    async def has_been_processed(self, event_id: str) -> bool:
        """Check if an event ID has already been handled."""

    async def record_event(
        self,
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        status: str,
    ) -> None:
        """Record an event for audit and idempotency."""
