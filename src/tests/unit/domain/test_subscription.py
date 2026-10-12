"""Unit tests for subscription domain entities and value objects."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.entities.plan import BillingPeriod, Plan
from app.domain.entities.subscription import Subscription, SubscriptionStatus
from app.domain.value_objects.plan_snapshot import PlanSnapshot
from app.domain.value_objects.usage_balance import UsageBalance


def test_create_valid_plan() -> None:
    plan = Plan(
        code="lite_monthly",
        name="Lite",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("499.00"),
        offer_price=Decimal("299.00"),
        max_seconds_per_request=30,
        max_usage_per_day=50,
    )
    assert plan.code == "lite_monthly"
    assert plan.max_seconds_per_request == 30
    assert plan.max_usage_per_day == 50
    assert plan.is_active is True
    assert plan.is_deleted is False


def test_plan_validation_rejects_empty_code_or_negative_values() -> None:
    with pytest.raises(ValueError):
        Plan(
            code="",
            name="Lite",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("100"),
            offer_price=Decimal("50"),
            max_seconds_per_request=30,
            max_usage_per_day=50,
        )

    with pytest.raises(ValueError):
        Plan(
            code="lite",
            name="Lite",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("-10"),
            offer_price=Decimal("50"),
            max_seconds_per_request=30,
            max_usage_per_day=50,
        )

    with pytest.raises(ValueError, match="Invalid billing period"):
        Plan(
            code="lite",
            name="Lite",
            billing_period="quarterly",
            actual_price=Decimal("100"),
            offer_price=Decimal("50"),
            max_seconds_per_request=30,
            max_usage_per_day=50,
        )


def test_billing_period_enum_parsing_and_durations() -> None:
    assert BillingPeriod.from_str("daily") == BillingPeriod.DAILY
    assert BillingPeriod.from_str("day") == BillingPeriod.DAILY
    assert BillingPeriod.DAILY.duration_days == 1

    assert BillingPeriod.from_str("weekly") == BillingPeriod.WEEKLY
    assert BillingPeriod.from_str("week") == BillingPeriod.WEEKLY
    assert BillingPeriod.WEEKLY.duration_days == 7

    assert BillingPeriod.from_str("monthly") == BillingPeriod.MONTHLY
    assert BillingPeriod.from_str("month") == BillingPeriod.MONTHLY
    assert BillingPeriod.from_str("MONTHLY") == BillingPeriod.MONTHLY
    assert BillingPeriod.MONTHLY.duration_days == 30

    assert BillingPeriod.from_str("yearly") == BillingPeriod.YEARLY
    assert BillingPeriod.from_str("year") == BillingPeriod.YEARLY
    assert BillingPeriod.YEARLY.duration_days == 365

    with pytest.raises(ValueError, match="Invalid billing period 'biweekly'"):
        BillingPeriod.from_str("biweekly")


def test_plan_snapshot_and_limits() -> None:
    snapshot = PlanSnapshot(
        plan_name="Pro",
        max_seconds_per_request=120,
        max_usage_per_day=150,
        price=Decimal("599.00"),
    )
    limits = snapshot.limits
    assert limits.max_seconds_per_request == 120
    assert limits.max_usage_per_day == 150


def test_subscription_active_lifecycle() -> None:
    now = datetime.now(UTC)
    snapshot = PlanSnapshot(
        plan_name="Lite",
        max_seconds_per_request=30,
        max_usage_per_day=50,
        price=Decimal("299.00"),
    )
    sub = Subscription(
        user_id="usr-123",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=1),
        current_period_end=now + timedelta(days=29),
        snapshot=snapshot,
    )
    assert sub.is_currently_active(now) is True

    # Expired in past
    past_sub = Subscription(
        user_id="usr-123",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=30),
        current_period_end=now - timedelta(days=1),
        snapshot=snapshot,
    )
    assert past_sub.is_currently_active(now) is False

    # Cancelled status
    cancelled_sub = Subscription(
        user_id="usr-123",
        status=SubscriptionStatus.CANCELLED,
        current_period_start=now - timedelta(days=1),
        current_period_end=now + timedelta(days=10),
        snapshot=snapshot,
    )
    assert cancelled_sub.is_currently_active(now) is False


def test_usage_balance() -> None:
    balance = UsageBalance(used_today=12, limit=50)
    assert balance.remaining == 38
    assert balance.is_exhausted is False

    exhausted = UsageBalance(used_today=50, limit=50)
    assert exhausted.remaining == 0
    assert exhausted.is_exhausted is True
