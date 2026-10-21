"""Subscription, payment, and quota tracking ports."""

from typing import Any, Protocol
from uuid import UUID

from app.domain.entities.subscription import Subscription


class SubscriptionRepository(Protocol):
    """Persistence contract for user subscriptions."""

    async def get_active_by_user_id(self, user_id: str) -> Subscription | None:
        """Fetch the most recent active or trialing subscription for a user."""

    async def get_latest_by_user_id(self, user_id: str) -> Subscription | None:
        """Fetch the most recent subscription for a user regardless of status."""

    async def get_by_external_id(self, external_id: str) -> Subscription | None:
        """Fetch subscription by provider external subscription ID."""

    async def save(self, subscription: Subscription) -> Subscription:
        """Persist subscription state."""

    async def get(self, **filters: Any) -> Subscription | None:
        """Get one subscription matching the supplied field filters."""

    async def get_by_id(self, subscription_id: UUID) -> Subscription | None: ...
