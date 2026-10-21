"""Unit tests for Subscription."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.subscription import (
    Subscription,
    SubscriptionOperationType,
    SubscriptionStatus,
)
from tests.factories.make_subscription import make_subscription_data


@pytest.fixture
def valid_subscription_data() -> dict:
    now = datetime.now(UTC)

    return {
        "user_id": "user-123",
        "status": SubscriptionStatus.ACTIVE,
        "current_period_start": now,
        "current_period_end": now + timedelta(days=30),
        "is_active": True,
        "snapshot_plan_name": "Pro Plan",
        "snapshot_max_seconds": 300,
        "snapshot_max_usage_per_day": 100,
        "snapshot_price": Decimal("799.00"),
        "snapshot_currency": "INR",
    }


def test_creates_subscription(
    valid_subscription_data: dict,
) -> None:
    subscription = Subscription(**valid_subscription_data)

    assert subscription.user_id == "user-123"
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.provider == "cashfree"
    assert subscription.is_active is True
    assert subscription.operation_type is SubscriptionOperationType.NEW
    assert subscription.snapshot_plan_name == "Pro Plan"
    assert subscription.snapshot_max_seconds == 300
    assert subscription.snapshot_max_usage_per_day == 100
    assert subscription.snapshot_price == Decimal("799.00")
    assert subscription.snapshot_currency == "INR"


def test_generates_subscription_id(
    valid_subscription_data: dict,
) -> None:
    subscription = Subscription(**valid_subscription_data)

    assert subscription.id is not None


def test_accepts_custom_identifiers(
    valid_subscription_data: dict,
) -> None:
    subscription_id = uuid4()
    plan_id = uuid4()
    related_id = uuid4()

    valid_subscription_data.update(
        id=subscription_id,
        plan_id=plan_id,
        related_subscription_id=related_id,
    )

    subscription = Subscription(**valid_subscription_data)

    assert subscription.id == subscription_id
    assert subscription.plan_id == plan_id
    assert subscription.related_subscription_id == related_id


@pytest.mark.parametrize("user_id", ["", " ", "   ", "\t"])
def test_rejects_empty_user_id(
    valid_subscription_data: dict,
    user_id: str,
) -> None:
    valid_subscription_data["user_id"] = user_id

    with pytest.raises(ValueError, match="user_id must not be empty"):
        Subscription(**valid_subscription_data)


def test_normalizes_user_id_and_provider(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["user_id"] = "  user-123  "
    valid_subscription_data["provider"] = "  CASHFREE  "

    subscription = Subscription(**valid_subscription_data)

    assert subscription.user_id == "user-123"
    assert subscription.provider == "cashfree"


def test_rejects_empty_provider(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["provider"] = " "

    with pytest.raises(ValueError, match="provider must not be empty"):
        Subscription(**valid_subscription_data)


def test_normalizes_status_string(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["status"] = "ACTIVE"

    subscription = Subscription(**valid_subscription_data)

    assert subscription.status is SubscriptionStatus.ACTIVE


def test_normalizes_operation_type_string(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["operation_type"] = "UPGRADE"

    subscription = Subscription(**valid_subscription_data)

    assert subscription.operation_type is SubscriptionOperationType.UPGRADE


def test_rejects_unknown_status(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["status"] = "UNKNOWN"

    with pytest.raises(ValueError):
        Subscription(**valid_subscription_data)


def test_rejects_unknown_operation_type(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["operation_type"] = "UNKNOWN"

    with pytest.raises(ValueError):
        Subscription(**valid_subscription_data)


def test_rejects_naive_period_start(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["current_period_start"] = datetime(2026, 1, 1)

    with pytest.raises(ValueError, match="timezone-aware"):
        Subscription(**valid_subscription_data)


def test_rejects_naive_period_end(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["current_period_end"] = datetime(2026, 2, 1)

    with pytest.raises(ValueError, match="timezone-aware"):
        Subscription(**valid_subscription_data)


def test_rejects_period_end_before_start(
    valid_subscription_data: dict,
) -> None:
    start = datetime.now(UTC)

    valid_subscription_data["current_period_start"] = start
    valid_subscription_data["current_period_end"] = start - timedelta(days=1)

    with pytest.raises(
        ValueError,
        match="current_period_end must be after",
    ):
        Subscription(**valid_subscription_data)


def test_rejects_equal_period_boundaries(
    valid_subscription_data: dict,
) -> None:
    now = datetime.now(UTC)

    valid_subscription_data["current_period_start"] = now
    valid_subscription_data["current_period_end"] = now

    with pytest.raises(ValueError, match="must be after"):
        Subscription(**valid_subscription_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("snapshot_max_seconds", 0),
        ("snapshot_max_seconds", -1),
        ("snapshot_max_seconds", True),
        ("snapshot_max_usage_per_day", 0),
        ("snapshot_max_usage_per_day", -1),
        ("snapshot_max_usage_per_day", True),
    ],
)
def test_rejects_invalid_snapshot_limits(
    valid_subscription_data: dict,
    field: str,
    value: int,
) -> None:
    valid_subscription_data[field] = value

    with pytest.raises(ValueError):
        Subscription(**valid_subscription_data)


def test_rejects_empty_snapshot_plan_name(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["snapshot_plan_name"] = "  "

    with pytest.raises(
        ValueError,
        match="snapshot_plan_name must not be empty",
    ):
        Subscription(**valid_subscription_data)


def test_rejects_negative_snapshot_price(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["snapshot_price"] = Decimal("-1")

    with pytest.raises(
        ValueError,
        match="snapshot_price must be finite and non-negative",
    ):
        Subscription(**valid_subscription_data)


def test_rejects_non_finite_snapshot_price(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["snapshot_price"] = Decimal("NaN")

    with pytest.raises(
        ValueError,
        match="snapshot_price must be finite and non-negative",
    ):
        Subscription(**valid_subscription_data)


def test_rejects_invalid_snapshot_currency(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["snapshot_currency"] = "US"

    with pytest.raises(ValueError, match="three-letter"):
        Subscription(**valid_subscription_data)


def test_normalizes_snapshot_currency(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["snapshot_currency"] = "inr"

    subscription = Subscription(**valid_subscription_data)

    assert subscription.snapshot_currency == "INR"


def test_limits_returns_snapshot_limits(
    valid_subscription_data: dict,
) -> None:
    subscription = Subscription(**valid_subscription_data)

    limits = subscription.limits

    assert limits.max_seconds_per_request == 300
    assert limits.max_usage_per_day == 100


def test_limits_rejects_incomplete_snapshot(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["snapshot_max_seconds"] = None

    subscription = Subscription(**valid_subscription_data)

    with pytest.raises(
        ValueError,
        match="does not have a complete plan snapshot",
    ):
        _ = subscription.limits


def test_inactive_flag_denies_access(
    valid_subscription_data: dict,
) -> None:
    valid_subscription_data["is_active"] = False

    subscription = Subscription(**valid_subscription_data)

    assert subscription.is_currently_active() is False


@pytest.mark.parametrize(
    "status",
    [
        SubscriptionStatus.PENDING,
        SubscriptionStatus.CANCELLED,
        SubscriptionStatus.EXPIRED,
        SubscriptionStatus.ON_HOLD,
        SubscriptionStatus.COMPLETED,
        SubscriptionStatus.CUSTOMER_CANCELLED,
        SubscriptionStatus.CUSTOMER_PAUSED,
        SubscriptionStatus.LINK_EXPIRED,
        SubscriptionStatus.BANK_APPROVAL_PENDING,
        SubscriptionStatus.CARD_EXPIRED,
    ],
)
def test_non_active_status_denies_access(
    valid_subscription_data: dict,
    status: SubscriptionStatus,
) -> None:
    valid_subscription_data["status"] = status

    subscription = Subscription(**valid_subscription_data)

    assert subscription.is_currently_active() is False


def test_active_subscription_grants_access(
    valid_subscription_data: dict,
) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    now = datetime(2026, 1, 15, tzinfo=UTC)

    valid_subscription_data["current_period_start"] = start
    valid_subscription_data["current_period_end"] = end

    subscription = Subscription(**valid_subscription_data)

    assert subscription.is_currently_active(now) is True


def test_access_denied_before_period_start(
    valid_subscription_data: dict,
) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    valid_subscription_data["current_period_start"] = start
    valid_subscription_data["current_period_end"] = start + timedelta(days=30)

    subscription = Subscription(**valid_subscription_data)

    assert subscription.is_currently_active(start - timedelta(seconds=1)) is False


def test_access_denied_at_period_end(
    valid_subscription_data: dict,
) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=30)

    valid_subscription_data["current_period_start"] = start
    valid_subscription_data["current_period_end"] = end

    subscription = Subscription(**valid_subscription_data)

    assert subscription.is_currently_active(end) is False


def test_access_denied_after_period_end(
    valid_subscription_data: dict,
) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=30)

    valid_subscription_data["current_period_start"] = start
    valid_subscription_data["current_period_end"] = end

    subscription = Subscription(**valid_subscription_data)

    assert subscription.is_currently_active(end + timedelta(seconds=1)) is False


def test_rejects_naive_now_argument(
    valid_subscription_data: dict,
) -> None:
    subscription = Subscription(**valid_subscription_data)

    with pytest.raises(ValueError, match="now must be timezone-aware"):
        subscription.is_currently_active(datetime(2026, 1, 15))


def test_subscription_is_mutable(
    valid_subscription_data: dict,
) -> None:
    subscription = Subscription(**valid_subscription_data)

    subscription.status = SubscriptionStatus.CANCELLED

    assert subscription.status is SubscriptionStatus.CANCELLED


def test_trial_subscription_requires_trial_dates():
    with pytest.raises(ValueError, match="trial_start and trial_end"):
        make_subscription_data(has_trial=True)


def test_trial_end_must_be_after_trial_start():
    now = datetime.now(UTC)

    with pytest.raises(ValueError, match="trial_end"):
        make_subscription_data(
            has_trial=True,
            trial_start=now,
            trial_end=now - timedelta(seconds=1),
        )


def test_non_trial_subscription_can_have_no_trial_dates():
    subscription = make_subscription_data()

    assert subscription.has_trial is False
    assert subscription.trial_start is None
    assert subscription.trial_end is None
