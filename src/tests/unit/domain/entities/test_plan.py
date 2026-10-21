"""Unit tests for Plan."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.entities.plan import BillingPeriod, Plan


@pytest.fixture
def valid_plan_data() -> dict:
    return {
        "code": "pro",
        "name": "Pro Plan",
        "billing_period": BillingPeriod.MONTHLY,
        "actual_price": Decimal("999.00"),
        "offer_price": Decimal("799.00"),
        "max_seconds_per_request": 300,
        "max_usage_per_day": 100,
    }


def test_creates_plan(valid_plan_data: dict) -> None:
    plan = Plan(**valid_plan_data)

    assert plan.code == "pro"
    assert plan.name == "Pro Plan"
    assert plan.billing_period is BillingPeriod.MONTHLY
    assert plan.actual_price == Decimal("999.00")
    assert plan.offer_price == Decimal("799.00")
    assert plan.max_seconds_per_request == 300
    assert plan.max_usage_per_day == 100
    assert plan.currency == "INR"
    assert plan.is_active is True
    assert plan.is_deleted is False
    assert isinstance(plan.id, UUID)


def test_normalizes_code_name_and_currency(
    valid_plan_data: dict,
) -> None:
    valid_plan_data.update(
        code="  pro  ",
        name="  Pro Plan  ",
        currency="inr",
    )

    plan = Plan(**valid_plan_data)

    assert plan.code == "pro"
    assert plan.name == "Pro Plan"
    assert plan.currency == "INR"


def test_normalizes_billing_period_string(
    valid_plan_data: dict,
) -> None:
    valid_plan_data["billing_period"] = "month"

    plan = Plan(**valid_plan_data)

    assert plan.billing_period is BillingPeriod.MONTHLY


@pytest.mark.parametrize("field", ["code", "name"])
@pytest.mark.parametrize("value", ["", " ", "   "])
def test_rejects_empty_code_or_name(
    valid_plan_data: dict,
    field: str,
    value: str,
) -> None:
    valid_plan_data[field] = value

    with pytest.raises(ValueError):
        Plan(**valid_plan_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actual_price", Decimal("-1")),
        ("offer_price", Decimal("-1")),
    ],
)
def test_rejects_negative_prices(
    valid_plan_data: dict,
    field: str,
    value: Decimal,
) -> None:
    valid_plan_data[field] = value

    with pytest.raises(ValueError, match="must not be negative"):
        Plan(**valid_plan_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actual_price", Decimal("NaN")),
        ("actual_price", Decimal("Infinity")),
        ("offer_price", Decimal("NaN")),
        ("offer_price", Decimal("Infinity")),
    ],
)
def test_rejects_non_finite_prices(
    valid_plan_data: dict,
    field: str,
    value: Decimal,
) -> None:
    valid_plan_data[field] = value

    with pytest.raises(ValueError, match="must be finite"):
        Plan(**valid_plan_data)


def test_rejects_offer_price_greater_than_actual_price(
    valid_plan_data: dict,
) -> None:
    valid_plan_data["actual_price"] = Decimal("100")
    valid_plan_data["offer_price"] = Decimal("101")

    with pytest.raises(ValueError, match="must not exceed"):
        Plan(**valid_plan_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actual_price", 999),
        ("offer_price", 799),
    ],
)
def test_rejects_non_decimal_prices(
    valid_plan_data: dict,
    field: str,
    value: int,
) -> None:
    valid_plan_data[field] = value

    with pytest.raises(TypeError, match="must be a Decimal"):
        Plan(**valid_plan_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_seconds_per_request", 0),
        ("max_seconds_per_request", -1),
        ("max_seconds_per_request", True),
        ("max_usage_per_day", 0),
        ("max_usage_per_day", -1),
        ("max_usage_per_day", True),
    ],
)
def test_rejects_invalid_usage_limits(
    valid_plan_data: dict,
    field: str,
    value: int,
) -> None:
    valid_plan_data[field] = value

    with pytest.raises(ValueError):
        Plan(**valid_plan_data)


@pytest.mark.parametrize("currency", ["", "IN", "INRR", "123"])
def test_rejects_invalid_currency(
    valid_plan_data: dict,
    currency: str,
) -> None:
    valid_plan_data["currency"] = currency

    with pytest.raises(ValueError, match="three-letter"):
        Plan(**valid_plan_data)


def test_rejects_unknown_billing_period(
    valid_plan_data: dict,
) -> None:
    valid_plan_data["billing_period"] = "hourly"

    with pytest.raises(ValueError, match="Invalid billing period"):
        Plan(**valid_plan_data)


def test_preserves_id_and_timestamps(
    valid_plan_data: dict,
) -> None:
    plan_id = uuid4()
    created_at = datetime.now(UTC)
    updated_at = datetime.now(UTC)

    valid_plan_data.update(
        id=plan_id,
        created_at=created_at,
        updated_at=updated_at,
    )

    plan = Plan(**valid_plan_data)

    assert plan.id == plan_id
    assert plan.created_at == created_at
    assert plan.updated_at == updated_at


def test_plan_is_mutable(valid_plan_data: dict) -> None:
    plan = Plan(**valid_plan_data)

    plan.name = "Updated Plan"

    assert plan.name == "Updated Plan"
