"""Unit tests for Credit."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.entities.credit import Credit


@pytest.fixture
def credit() -> Credit:
    return Credit(
        user_id="user-123",
        subscription_seconds=100,
        top_up_seconds=50,
    )


def test_creates_credit(credit: Credit) -> None:
    assert credit.user_id == "user-123"
    assert credit.subscription_seconds == 100
    assert credit.top_up_seconds == 50
    assert credit.total_seconds == 150


@pytest.mark.parametrize("user_id", ["", " ", "   "])
def test_rejects_empty_user_id(user_id: str) -> None:
    with pytest.raises(ValueError, match="user_id cannot be empty"):
        Credit(user_id=user_id)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subscription_seconds", -1),
        ("subscription_seconds", True),
        ("subscription_seconds", 1.5),
        ("top_up_seconds", -1),
        ("top_up_seconds", False),
        ("top_up_seconds", "10"),
    ],
)
def test_rejects_invalid_balances(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        Credit(user_id="user-123", **{field: value})


def test_grant_subscription(credit: Credit) -> None:
    credit.grant_subscription(25)

    assert credit.subscription_seconds == 125
    assert credit.top_up_seconds == 50
    assert credit.total_seconds == 175


def test_grant_top_up(credit: Credit) -> None:
    credit.grant_top_up(75)

    assert credit.subscription_seconds == 100
    assert credit.top_up_seconds == 125
    assert credit.total_seconds == 225


@pytest.mark.parametrize("seconds", [0, -1, True, 1.5])
def test_rejects_invalid_grants(credit: Credit, seconds: int) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        credit.grant_subscription(seconds)

    with pytest.raises(ValueError, match="positive integer"):
        credit.grant_top_up(seconds)


def test_consumes_subscription_credits_first(credit: Credit) -> None:
    subscription_used, top_up_used = credit.consume(80)

    assert (subscription_used, top_up_used) == (80, 0)
    assert credit.subscription_seconds == 20
    assert credit.top_up_seconds == 50


def test_consumes_top_up_when_subscription_is_exhausted(
    credit: Credit,
) -> None:
    subscription_used, top_up_used = credit.consume(130)

    assert (subscription_used, top_up_used) == (100, 30)
    assert credit.subscription_seconds == 0
    assert credit.top_up_seconds == 20


def test_consumes_only_top_up_when_subscription_balance_is_zero() -> None:
    credit = Credit(
        user_id="user-123",
        subscription_seconds=0,
        top_up_seconds=50,
    )

    assert credit.consume(20) == (0, 20)
    assert credit.total_seconds == 30


def test_rejects_consumption_above_balance(credit: Credit) -> None:
    with pytest.raises(ValueError, match="insufficient credits"):
        credit.consume(151)

    assert credit.subscription_seconds == 100
    assert credit.top_up_seconds == 50


@pytest.mark.parametrize("seconds", [0, -1, True, 1.5])
def test_rejects_invalid_consumption(
    credit: Credit,
    seconds: int,
) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        credit.consume(seconds)


def test_preserves_id_and_timestamps() -> None:
    credit_id = uuid4()
    timestamp = datetime.now(UTC)

    credit = Credit(
        user_id="user-123",
        id=credit_id,
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert credit.id == credit_id
    assert credit.created_at == timestamp
    assert credit.updated_at == timestamp
