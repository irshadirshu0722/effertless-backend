"""Factories for subscription domain entities."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.entities.subscription import (
    Subscription,
    SubscriptionStatus,
)


def make_subscription_data(**overrides) -> Subscription:
    data = {
        "user_id": "user-123",
        "status": SubscriptionStatus.PENDING,
        "provider": "cashfree",
        "current_period_start": datetime.now(UTC),
        "current_period_end": datetime.now(UTC) + timedelta(days=30),
        "snapshot_plan_name": "Pro",
        "snapshot_max_seconds": 120,
        "snapshot_price": Decimal("20.00"),
        "snapshot_currency": "INR",
        "has_trial": False,
        "trial_start": None,
        "trial_end": None,
    }
    data.update(overrides)
    return Subscription(**data)
