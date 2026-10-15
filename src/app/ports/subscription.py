"""Subscription, payment, and quota tracking ports."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.domain.entities.plan import Plan
from app.domain.entities.subscription import Subscription


class PlanRepository(Protocol):
    """Persistence contract for subscription plans."""

    async def list_active(self) -> Sequence[Plan]:
        """List all active, non-deleted plans."""

    async def get_by_code(self, code: str) -> Plan | None:
        """Fetch a plan by unique code."""

    async def get_by_id(self, plan_id: UUID) -> Plan | None:
        """Fetch a plan by unique ID."""

    async def save(self, plan: Plan) -> Plan:
        """Create or update a plan."""


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


class UsageTracker(Protocol):
    """Fast cache contract for daily usage counting."""

    async def get_today_usage(self, user_id: str) -> int:
        """Return the number of requests made by the user today."""

    async def increment_today_usage(self, user_id: str) -> int:
        """Increment and return the updated count of requests made today."""


class PaymentGateway(Protocol):
    """External payment gateway abstraction (e.g. Cashfree)."""

    async def create_plan(self, plan: Plan) -> bool:
        """Create a subscription plan with the payment provider."""

    async def delete_plan(self, plan_code: str) -> bool:
        """Delete a subscription plan from the payment provider."""

    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str | None,
        plan: Plan,
        return_url: str,
        first_charge_time: datetime | None = None,
    ) -> tuple[str, str]:
        """Create a subscription session. Returns (external_subscription_id, checkout_session_id)."""

    async def cancel_subscription(self, external_subscription_id: str) -> bool:
        """Request subscription cancellation with provider."""

    def verify_webhook_signature(
        self,
        raw_payload: bytes,
        signature: str,
        timestamp: str,
    ) -> bool:
        """Cryptographically verify authenticity of webhook payload."""


class WebhookEventRepository(Protocol):
    """Deduplication and audit log for incoming webhook events."""

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
