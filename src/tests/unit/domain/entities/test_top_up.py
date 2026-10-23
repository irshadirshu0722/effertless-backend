"""Unit tests for TopUp."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.top_up import TopUp, TopUpStatus


@pytest.fixture
def top_up() -> TopUp:
    return TopUp(
        user_id="user-123",
        seconds=3600,
        amount=Decimal("99.00"),
    )


def test_creates_top_up(top_up: TopUp) -> None:
    assert top_up.user_id == "user-123"
    assert top_up.seconds == 3600
    assert top_up.amount == Decimal("99.00")
    assert top_up.currency == "INR"
    assert top_up.status is TopUpStatus.PENDING
    assert top_up.completed_at is None


@pytest.mark.parametrize("user_id", ["", " "])
def test_rejects_empty_user_id(user_id: str) -> None:
    with pytest.raises(ValueError, match="user_id"):
        TopUp(user_id=user_id, seconds=60, amount=Decimal("1"))


@pytest.mark.parametrize("seconds", [0, -1, True, 1.5, "60"])
def test_rejects_invalid_seconds(seconds: object) -> None:
    with pytest.raises(ValueError, match="seconds"):
        TopUp(user_id="user-123", seconds=seconds, amount=Decimal("1"))


@pytest.mark.parametrize(
    "amount",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        "invalid",
        True,
    ],
)
def test_rejects_invalid_amount(amount: object) -> None:
    with pytest.raises(ValueError, match="amount"):
        TopUp(user_id="user-123", seconds=60, amount=amount)


@pytest.mark.parametrize("currency", ["", "IN", "INRR", "123", "US$"])
def test_rejects_invalid_currency(currency: str) -> None:
    with pytest.raises(ValueError, match="three-letter"):
        TopUp(
            user_id="user-123",
            seconds=60,
            amount=Decimal("1"),
            currency=currency,
        )


def test_normalizes_values() -> None:
    top_up = TopUp(
        user_id=" user-123 ",
        seconds=60,
        amount="10.00",
        currency="inr",
        provider=" CASHFREE ",
    )

    assert top_up.user_id == "user-123"
    assert top_up.currency == "INR"
    assert top_up.provider == "cashfree"
    assert top_up.amount == Decimal("10.00")


def test_completes_pending_top_up(top_up: TopUp) -> None:
    top_up.complete("payment-123")

    assert top_up.status is TopUpStatus.COMPLETED
    assert top_up.external_payment_id == "payment-123"
    assert top_up.completed_at is not None
    assert top_up.updated_at == top_up.completed_at


def test_rejects_empty_payment_id(top_up: TopUp) -> None:
    with pytest.raises(ValueError, match="external_payment_id"):
        top_up.complete(" ")


def test_cannot_complete_top_up_twice(top_up: TopUp) -> None:
    top_up.complete("payment-123")

    with pytest.raises(ValueError, match="pending"):
        top_up.complete("payment-456")


def test_fails_pending_top_up(top_up: TopUp) -> None:
    top_up.fail()

    assert top_up.status is TopUpStatus.FAILED


def test_cancels_pending_top_up(top_up: TopUp) -> None:
    top_up.cancel()

    assert top_up.status is TopUpStatus.CANCELLED


def test_cannot_fail_completed_top_up(top_up: TopUp) -> None:
    top_up.complete()

    with pytest.raises(ValueError, match="pending"):
        top_up.fail()


def test_cannot_cancel_completed_top_up(top_up: TopUp) -> None:
    top_up.complete()

    with pytest.raises(ValueError, match="pending"):
        top_up.cancel()


def test_completed_top_up_requires_completion_time() -> None:
    timestamp = datetime.now(UTC)

    top_up = TopUp(
        user_id="user-123",
        seconds=60,
        amount=Decimal("10"),
        status=TopUpStatus.COMPLETED,
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert top_up.completed_at == timestamp


def test_preserves_id() -> None:
    top_up_id = uuid4()

    top_up = TopUp(
        user_id="user-123",
        seconds=60,
        amount=Decimal("10"),
        id=top_up_id,
    )

    assert top_up.id == top_up_id
