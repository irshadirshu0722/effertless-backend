"""Unit tests for BillingPeriod."""

import pytest

from app.domain.entities.plan import BillingPeriod


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("daily", BillingPeriod.DAILY),
        ("day", BillingPeriod.DAILY),
        ("weekly", BillingPeriod.WEEKLY),
        ("week", BillingPeriod.WEEKLY),
        ("monthly", BillingPeriod.MONTHLY),
        ("month", BillingPeriod.MONTHLY),
        ("yearly", BillingPeriod.YEARLY),
        ("year", BillingPeriod.YEARLY),
        (" MONTH ", BillingPeriod.MONTHLY),
        ("YEARLY", BillingPeriod.YEARLY),
    ],
)
def test_from_str_normalizes_supported_values(
    value: str,
    expected: BillingPeriod,
) -> None:
    assert BillingPeriod.from_str(value) is expected


@pytest.mark.parametrize(
    ("period", "expected_days"),
    [
        (BillingPeriod.DAILY, 1),
        (BillingPeriod.WEEKLY, 7),
        (BillingPeriod.MONTHLY, 30),
        (BillingPeriod.YEARLY, 365),
    ],
)
def test_duration_days(
    period: BillingPeriod,
    expected_days: int,
) -> None:
    assert period.duration_days == expected_days


def test_from_str_accepts_existing_enum() -> None:
    assert BillingPeriod.from_str(BillingPeriod.MONTHLY) is BillingPeriod.MONTHLY


@pytest.mark.parametrize("value", ["hourly", "", "unknown"])
def test_from_str_rejects_unsupported_values(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid billing period"):
        BillingPeriod.from_str(value)
