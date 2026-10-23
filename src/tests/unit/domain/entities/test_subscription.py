from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.subscription import (
    SubscriptionOperationType,
    SubscriptionStatus,
)
from tests.factories import make_subscription_data


def test_create_subscription_with_default_values():
    subscription = make_subscription_data()

    assert subscription.user_id == "user-123"
    assert subscription.status is SubscriptionStatus.PENDING
    assert subscription.provider == "cashfree"
    assert subscription.operation_type is SubscriptionOperationType.NEW
    assert subscription.is_active is False
    assert subscription.has_trial is False


def test_subscription_normalizes_user_id_and_provider():
    subscription = make_subscription_data(
        user_id="  user-123  ",
        provider=" CASHFREE ",
    )

    assert subscription.user_id == "user-123"
    assert subscription.provider == "cashfree"


def test_subscription_rejects_empty_user_id():
    with pytest.raises(ValueError, match="user_id must not be empty"):
        make_subscription_data(user_id="  ")


def test_subscription_rejects_empty_provider():
    with pytest.raises(ValueError, match="provider must not be empty"):
        make_subscription_data(provider="  ")


@pytest.mark.parametrize(
    "status",
    ["PENDING", "ACTIVE", "CANCELLED", "EXPIRED"],
)
def test_subscription_converts_status_string_to_enum(status):
    subscription = make_subscription_data(status=status)

    assert subscription.status is SubscriptionStatus(status)


def test_subscription_rejects_unknown_status():
    with pytest.raises(ValueError):
        make_subscription_data(status="UNKNOWN")


@pytest.mark.parametrize(
    "operation_type",
    ["NEW", "RENEWAL", "UPGRADE", "DOWNGRADE"],
)
def test_subscription_converts_operation_type_string_to_enum(operation_type):
    subscription = make_subscription_data(operation_type=operation_type)

    assert subscription.operation_type is SubscriptionOperationType(operation_type)


def test_subscription_rejects_unknown_operation_type():
    with pytest.raises(ValueError):
        make_subscription_data(operation_type="UNKNOWN")


def test_subscription_rejects_naive_period_start():
    with pytest.raises(
        ValueError,
        match="current_period_start must be timezone-aware",
    ):
        make_subscription_data(
            current_period_start=datetime(2026, 10, 1),
        )


def test_subscription_rejects_naive_period_end():
    with pytest.raises(
        ValueError,
        match="current_period_end must be timezone-aware",
    ):
        make_subscription_data(
            current_period_end=datetime(2026, 11, 1),
        )


def test_subscription_rejects_end_before_start():
    start = datetime(2026, 10, 1, tzinfo=UTC)

    with pytest.raises(
        ValueError,
        match="current_period_end must be after current_period_start",
    ):
        make_subscription_data(
            current_period_start=start,
            current_period_end=start - timedelta(seconds=1),
        )


def test_subscription_rejects_equal_period_dates():
    start = datetime(2026, 10, 1, tzinfo=UTC)

    with pytest.raises(
        ValueError,
        match="current_period_end must be after current_period_start",
    ):
        make_subscription_data(
            current_period_start=start,
            current_period_end=start,
        )


def test_subscription_rejects_naive_cancelled_at():
    with pytest.raises(
        ValueError,
        match="cancelled_at must be timezone-aware",
    ):
        make_subscription_data(
            cancelled_at=datetime(2026, 10, 10),
        )


def test_subscription_normalizes_snapshot_plan_name():
    subscription = make_subscription_data(
        snapshot_plan_name="  Pro  ",
    )

    assert subscription.snapshot_plan_name == "Pro"


def test_subscription_rejects_empty_snapshot_plan_name():
    with pytest.raises(
        ValueError,
        match="snapshot_plan_name must not be empty",
    ):
        make_subscription_data(snapshot_plan_name="  ")


def test_subscription_rejects_non_positive_snapshot_seconds():
    for seconds in (0, -1):
        with pytest.raises(
            ValueError,
            match="snapshot_max_seconds must be a positive integer",
        ):
            make_subscription_data(snapshot_max_seconds=seconds)


@pytest.mark.parametrize("seconds", [True, 1.5, "120"])
def test_subscription_rejects_non_integer_snapshot_seconds(seconds):
    with pytest.raises(
        ValueError,
        match="snapshot_max_seconds must be a positive integer",
    ):
        make_subscription_data(snapshot_max_seconds=seconds)


def test_subscription_allows_missing_snapshot_fields_in_domain():
    # Snapshot completeness is required when persisting, not necessarily
    # while constructing the domain entity.
    subscription = make_subscription_data(
        snapshot_max_seconds=None,
        snapshot_price=None,
        snapshot_currency=None,
        snapshot_plan_name=None,
    )

    assert subscription.snapshot_max_seconds is None
    assert subscription.snapshot_price is None
    assert subscription.snapshot_currency is None


def test_subscription_rejects_non_decimal_snapshot_price():
    with pytest.raises(TypeError, match="snapshot_price must be a Decimal"):
        make_subscription_data(snapshot_price=20.00)


@pytest.mark.parametrize("price", [Decimal("-1"), Decimal("NaN"), Decimal("Infinity")])
def test_subscription_rejects_invalid_snapshot_price(price):
    with pytest.raises(
        ValueError,
        match="snapshot_price must be finite and non-negative",
    ):
        make_subscription_data(snapshot_price=price)


def test_subscription_normalizes_snapshot_currency():
    subscription = make_subscription_data(snapshot_currency=" pln ")

    assert subscription.snapshot_currency == "PLN"


@pytest.mark.parametrize(
    "currency",
    ["", "PL", "PLNN", "12!"],
)
def test_subscription_rejects_invalid_snapshot_currency(currency):
    with pytest.raises(
        ValueError,
        match="snapshot_currency must be a three-letter code",
    ):
        make_subscription_data(snapshot_currency=currency)


def test_trial_subscription_requires_trial_dates():
    with pytest.raises(
        ValueError,
        match="trial_start and trial_end are required",
    ):
        make_subscription_data(has_trial=True)


def test_trial_subscription_accepts_valid_dates():
    start = datetime(2026, 10, 1, tzinfo=UTC)
    end = start + timedelta(days=7)

    subscription = make_subscription_data(
        has_trial=True,
        trial_start=start,
        trial_end=end,
    )

    assert subscription.has_trial is True
    assert subscription.trial_start == start
    assert subscription.trial_end == end


def test_trial_end_must_be_after_trial_start():
    start = datetime(2026, 10, 1, tzinfo=UTC)

    with pytest.raises(
        ValueError,
        match="trial_end must be later than trial_start",
    ):
        make_subscription_data(
            has_trial=True,
            trial_start=start,
            trial_end=start,
        )


def test_trial_dates_must_be_timezone_aware():
    start = datetime(2026, 10, 1)
    end = datetime(2026, 10, 8)

    # Once the entity enforces timezone awareness for trial dates,
    # this should be rejected.
    with pytest.raises(ValueError):
        make_subscription_data(
            has_trial=True,
            trial_start=start,
            trial_end=end,
        )


def test_non_trial_subscription_can_have_no_trial_dates():
    subscription = make_subscription_data(
        has_trial=False,
        trial_start=None,
        trial_end=None,
    )

    assert subscription.has_trial is False
    assert subscription.trial_start is None
    assert subscription.trial_end is None


def test_is_currently_active_when_inside_period():
    start = datetime(2026, 10, 1, tzinfo=UTC)
    end = datetime(2026, 11, 1, tzinfo=UTC)
    now = datetime(2026, 10, 15, tzinfo=UTC)

    subscription = make_subscription_data(
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
        current_period_start=start,
        current_period_end=end,
    )

    assert subscription.is_currently_active(now) is True


def test_is_currently_active_is_false_when_not_enabled():
    now = datetime(2026, 10, 15, tzinfo=UTC)

    subscription = make_subscription_data(
        status=SubscriptionStatus.ACTIVE,
        is_active=False,
    )

    assert subscription.is_currently_active(now) is False


def test_is_currently_active_is_false_before_period_start():
    start = datetime(2026, 10, 1, tzinfo=UTC)

    subscription = make_subscription_data(
        is_active=True,
        current_period_start=start,
        current_period_end=start + timedelta(days=30),
    )

    assert subscription.is_currently_active(start - timedelta(seconds=1)) is False


def test_is_currently_active_is_false_at_period_end():
    start = datetime(2026, 10, 1, tzinfo=UTC)
    end = start + timedelta(days=30)

    subscription = make_subscription_data(
        is_active=True,
        current_period_start=start,
        current_period_end=end,
    )

    assert subscription.is_currently_active(end) is False


def test_is_currently_active_rejects_naive_now():
    subscription = make_subscription_data(is_active=True)

    with pytest.raises(ValueError, match="now must be timezone-aware"):
        subscription.is_currently_active(datetime(2026, 10, 15))


def test_subscription_preserves_related_ids():
    plan_id = uuid4()
    related_id = uuid4()

    subscription = make_subscription_data(
        plan_id=plan_id,
        related_subscription_id=related_id,
    )

    assert subscription.plan_id == plan_id
    assert subscription.related_subscription_id == related_id


def test_subscription_preserves_external_identifiers():
    subscription = make_subscription_data(
        external_subscription_id="cf-sub-123",
        external_customer_id="cf-customer-123",
    )

    assert subscription.external_subscription_id == "cf-sub-123"
    assert subscription.external_customer_id == "cf-customer-123"
