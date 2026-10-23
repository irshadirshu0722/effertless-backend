"""Unit tests for the Plan domain entity."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.entities.plan import Plan, PlanCode


@pytest.fixture
def valid_plan_data() -> dict:
    return {
        "code": PlanCode.PRO,
        "name": "Pro",
        "monthly_seconds": 36000,
        "actual_price": Decimal("999.00"),
        "offer_price": Decimal("799.00"),
    }


def test_creates_plan(valid_plan_data: dict) -> None:
    plan = Plan(**valid_plan_data)

    assert plan.code is PlanCode.PRO
    assert plan.name == "Pro"
    assert plan.monthly_seconds == 36000
    assert plan.actual_price == Decimal("999.00")
    assert plan.offer_price == Decimal("799.00")
    assert plan.currency == "INR"
    assert plan.is_active is True
    assert plan.is_deleted is False
    assert isinstance(plan.id, UUID)


@pytest.mark.parametrize(
    ("code", "name"),
    [
        (PlanCode.BASIC, "Basic"),
        (PlanCode.STANDARD, "Standard"),
        (PlanCode.PRO, "Pro"),
    ],
)
def test_accepts_supported_plans(
    valid_plan_data: dict,
    code: PlanCode,
    name: str,
) -> None:
    valid_plan_data.update(code=code, name=name)

    plan = Plan(**valid_plan_data)

    assert plan.code is code
    assert plan.name == name


@pytest.mark.parametrize(
    ("code", "name"),
    [
        ("basic", "Basic"),
        (" BASIC ", "Basic"),
        ("standard", "Standard"),
        (" pro ", "Pro"),
    ],
)
def test_normalizes_plan_code(
    valid_plan_data: dict,
    code: str,
    name: str,
) -> None:
    valid_plan_data.update(code=code, name=name)

    plan = Plan(**valid_plan_data)

    assert plan.name == name
    assert plan.code is PlanCode(name.upper())


@pytest.mark.parametrize(
    "code",
    [
        "",
        " ",
        "premium",
        "enterprise",
        "monthly",
    ],
)
def test_rejects_unsupported_plan_code(
    valid_plan_data: dict,
    code: str,
) -> None:
    valid_plan_data["code"] = code

    with pytest.raises(ValueError, match="code must be"):
        Plan(**valid_plan_data)


@pytest.mark.parametrize(
    ("code", "name"),
    [
        (PlanCode.BASIC, "Basic Plan"),
        (PlanCode.STANDARD, "Standard Plan"),
        (PlanCode.PRO, "Premium"),
    ],
)
def test_rejects_name_not_matching_plan_code(
    valid_plan_data: dict,
    code: PlanCode,
    name: str,
) -> None:
    valid_plan_data.update(code=code, name=name)

    with pytest.raises(ValueError, match="name for"):
        Plan(**valid_plan_data)


@pytest.mark.parametrize("name", ["", " ", "   "])
def test_rejects_empty_name(
    valid_plan_data: dict,
    name: str,
) -> None:
    valid_plan_data["name"] = name

    with pytest.raises(ValueError, match="name cannot be empty"):
        Plan(**valid_plan_data)


def test_normalizes_name_and_currency(
    valid_plan_data: dict,
) -> None:
    valid_plan_data.update(
        name="  Pro  ",
        currency="inr",
    )

    plan = Plan(**valid_plan_data)

    assert plan.name == "Pro"
    assert plan.currency == "INR"


@pytest.mark.parametrize(
    "monthly_seconds",
    [0, -1, -3600, True, False, 1.5, "3600", None],
)
def test_rejects_invalid_monthly_seconds(
    valid_plan_data: dict,
    monthly_seconds: object,
) -> None:
    valid_plan_data["monthly_seconds"] = monthly_seconds

    with pytest.raises(
        ValueError,
        match="monthly_seconds must be a positive integer",
    ):
        Plan(**valid_plan_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actual_price", Decimal("-1")),
        ("offer_price", Decimal("-1")),
        ("actual_price", Decimal("-0.01")),
        ("offer_price", Decimal("-0.01")),
    ],
)
def test_rejects_negative_prices(
    valid_plan_data: dict,
    field: str,
    value: Decimal,
) -> None:
    valid_plan_data[field] = value

    with pytest.raises(ValueError, match="cannot be negative"):
        Plan(**valid_plan_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actual_price", Decimal("NaN")),
        ("actual_price", Decimal("Infinity")),
        ("actual_price", Decimal("-Infinity")),
        ("offer_price", Decimal("NaN")),
        ("offer_price", Decimal("Infinity")),
        ("offer_price", Decimal("-Infinity")),
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actual_price", True),
        ("offer_price", False),
        ("actual_price", "not-a-price"),
        ("offer_price", object()),
    ],
)
def test_rejects_invalid_price_values(
    valid_plan_data: dict,
    field: str,
    value: object,
) -> None:
    valid_plan_data[field] = value

    with pytest.raises(ValueError):
        Plan(**valid_plan_data)


@pytest.mark.parametrize(
    ("actual_price", "offer_price"),
    [
        ("100.00", "100.01"),
        ("100.00", "101.00"),
    ],
)
def test_rejects_offer_price_greater_than_actual_price(
    valid_plan_data: dict,
    actual_price: str,
    offer_price: str,
) -> None:
    valid_plan_data["actual_price"] = Decimal(actual_price)
    valid_plan_data["offer_price"] = Decimal(offer_price)

    with pytest.raises(
        ValueError,
        match="offer_price cannot exceed actual_price",
    ):
        Plan(**valid_plan_data)


def test_allows_offer_price_equal_to_actual_price(
    valid_plan_data: dict,
) -> None:
    valid_plan_data["actual_price"] = Decimal("100.00")
    valid_plan_data["offer_price"] = Decimal("100.00")

    plan = Plan(**valid_plan_data)

    assert plan.offer_price == plan.actual_price


def test_allows_missing_offer_price(
    valid_plan_data: dict,
) -> None:
    valid_plan_data["offer_price"] = None

    plan = Plan(**valid_plan_data)

    assert plan.offer_price is None
    assert plan.effective_price == Decimal("999.00")


@pytest.mark.parametrize(
    ("offer_price", "expected"),
    [
        (Decimal("799.00"), Decimal("799.00")),
        (None, Decimal("999.00")),
    ],
)
def test_effective_price(
    valid_plan_data: dict,
    offer_price: Decimal | None,
    expected: Decimal,
) -> None:
    valid_plan_data["offer_price"] = offer_price

    plan = Plan(**valid_plan_data)

    assert plan.effective_price == expected


@pytest.mark.parametrize(
    "currency",
    ["", " ", "IN", "INRR", "123", "US$", "éUR"],
)
def test_rejects_invalid_currency(
    valid_plan_data: dict,
    currency: str,
) -> None:
    valid_plan_data["currency"] = currency

    with pytest.raises(ValueError, match="three-letter"):
        Plan(**valid_plan_data)


@pytest.mark.parametrize(
    ("is_active", "is_deleted", "expected"),
    [
        (True, False, True),
        (False, False, False),
        (True, True, False),
        (False, True, False),
    ],
)
def test_is_available(
    valid_plan_data: dict,
    is_active: bool,
    is_deleted: bool,
    expected: bool,
) -> None:
    valid_plan_data.update(
        is_active=is_active,
        is_deleted=is_deleted,
    )

    plan = Plan(**valid_plan_data)

    assert plan.is_available is expected


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


@pytest.mark.parametrize("field", ["created_at", "updated_at"])
def test_rejects_naive_timestamps(
    valid_plan_data: dict,
    field: str,
) -> None:
    valid_plan_data[field] = datetime(2026, 1, 1)

    with pytest.raises(ValueError, match="timezone-aware"):
        Plan(**valid_plan_data)


def test_plan_is_mutable(valid_plan_data: dict) -> None:
    plan = Plan(**valid_plan_data)

    plan.actual_price = Decimal("1200.00")

    assert plan.actual_price == Decimal("1200.00")
