"""Factories for subscription domain entities."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.entities.subscription import (
    Subscription,
    SubscriptionOperationType,
    SubscriptionStatus,
)


def make_subscription_data(
    *,
    id: UUID | None = None,
    user_id: str = "user-123",
    plan_id: UUID | None = None,
    status: SubscriptionStatus = SubscriptionStatus.PENDING,
    provider: str = "cashfree",
    external_subscription_id: str | None = None,
    external_customer_id: str | None = None,
    current_period_start: datetime | None = None,
    current_period_end: datetime | None = None,
    cancelled_at: datetime | None = None,
    is_active: bool = False,
    operation_type: SubscriptionOperationType = SubscriptionOperationType.NEW,
    related_subscription_id: UUID | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    snapshot_plan_name: str | None = "Pro",
    snapshot_max_seconds: int | None = 120,
    snapshot_max_usage_per_day: int | None = 100,
    snapshot_price: Decimal | None = Decimal("20.00"),
    snapshot_currency: str | None = "PLN",
    has_trial: bool = False,
    trial_start: datetime | None = None,
    trial_end: datetime | None = None,
) -> Subscription:
    """Build a valid subscription for tests."""
    now = datetime.now(UTC)

    return Subscription(
        id=id or uuid4(),
        user_id=user_id,
        plan_id=plan_id,
        status=status,
        provider=provider,
        external_subscription_id=external_subscription_id,
        external_customer_id=external_customer_id,
        current_period_start=current_period_start or now,
        current_period_end=current_period_end or now + timedelta(days=30),
        cancelled_at=cancelled_at,
        is_active=is_active,
        operation_type=operation_type,
        related_subscription_id=related_subscription_id,
        created_at=created_at or now,
        updated_at=updated_at or now,
        snapshot_plan_name=snapshot_plan_name,
        snapshot_max_seconds=snapshot_max_seconds,
        snapshot_max_usage_per_day=snapshot_max_usage_per_day,
        snapshot_price=snapshot_price,
        snapshot_currency=snapshot_currency,
        has_trial=has_trial,
        trial_start=trial_start,
        trial_end=trial_end,
    )
