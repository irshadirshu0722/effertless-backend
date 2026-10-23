"""Unit tests for CreditTransaction."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.entities.credit_transaction import (
    CreditTransaction,
    CreditTransactionType,
)


@pytest.fixture
def transaction() -> CreditTransaction:
    return CreditTransaction(
        user_id="user-301",
        transaction_type=CreditTransactionType.SUBSCRIPTION_GRANTED,
        subscription_delta=3600,
        top_up_delta=0,
        subscription_balance_after=3600,
        top_up_balance_after=0,
    )


def test_creates_transaction(transaction: CreditTransaction) -> None:
    assert transaction.user_id == "user-301"
    assert transaction.transaction_type is (CreditTransactionType.SUBSCRIPTION_GRANTED)
    assert transaction.subscription_delta == 3600
    assert transaction.top_up_delta == 0
    assert transaction.subscription_balance_after == 3600
    assert transaction.top_up_balance_after == 0


def test_normalizes_user_id_and_description() -> None:
    transaction = CreditTransaction(
        user_id=" user-301 ",
        transaction_type=CreditTransactionType.ADJUSTMENT,
        subscription_delta=100,
        top_up_delta=0,
        subscription_balance_after=100,
        top_up_balance_after=0,
        description="  Admin adjustment  ",
    )

    assert transaction.user_id == "user-301"
    assert transaction.description == "Admin adjustment"


@pytest.mark.parametrize("user_id", ["", " ", "   "])
def test_rejects_empty_user_id(user_id: str) -> None:
    with pytest.raises(ValueError, match="user_id"):
        CreditTransaction(
            user_id=user_id,
            transaction_type=CreditTransactionType.ADJUSTMENT,
            subscription_delta=1,
            top_up_delta=0,
            subscription_balance_after=1,
            top_up_balance_after=0,
        )


def test_accepts_string_transaction_type() -> None:
    transaction = CreditTransaction(
        user_id="user-301",
        transaction_type="TOP_UP_PURCHASED",
        subscription_delta=0,
        top_up_delta=500,
        subscription_balance_after=0,
        top_up_balance_after=500,
    )

    assert transaction.transaction_type is (CreditTransactionType.TOP_UP_PURCHASED)


def test_rejects_invalid_transaction_type() -> None:
    with pytest.raises(ValueError, match="transaction type"):
        CreditTransaction(
            user_id="user-301",
            transaction_type="UNKNOWN",
            subscription_delta=1,
            top_up_delta=0,
            subscription_balance_after=1,
            top_up_balance_after=0,
        )


def test_rejects_transaction_with_no_balance_change() -> None:
    with pytest.raises(ValueError, match="change at least one balance"):
        CreditTransaction(
            user_id="user-301",
            transaction_type=CreditTransactionType.ADJUSTMENT,
            subscription_delta=0,
            top_up_delta=0,
            subscription_balance_after=100,
            top_up_balance_after=50,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subscription_delta", True),
        ("subscription_delta", 1.5),
        ("top_up_delta", "10"),
        ("subscription_balance_after", False),
        ("top_up_balance_after", 1.5),
    ],
)
def test_rejects_non_integer_values(
    field: str,
    value: object,
) -> None:
    data = {
        "user_id": "user-301",
        "transaction_type": CreditTransactionType.ADJUSTMENT,
        "subscription_delta": 1,
        "top_up_delta": 0,
        "subscription_balance_after": 1,
        "top_up_balance_after": 0,
    }
    data[field] = value

    with pytest.raises(ValueError, match="must be an integer"):
        CreditTransaction(**data)


def test_rejects_negative_subscription_balance() -> None:
    with pytest.raises(ValueError, match="subscription balance"):
        CreditTransaction(
            user_id="user-301",
            transaction_type=CreditTransactionType.SUBSCRIPTION_CONSUMED,
            subscription_delta=-10,
            top_up_delta=0,
            subscription_balance_after=-10,
            top_up_balance_after=0,
        )


def test_rejects_negative_top_up_balance() -> None:
    with pytest.raises(ValueError, match="top-up balance"):
        CreditTransaction(
            user_id="user-301",
            transaction_type=CreditTransactionType.TOP_UP_CONSUMED,
            subscription_delta=0,
            top_up_delta=-10,
            subscription_balance_after=0,
            top_up_balance_after=-10,
        )


def test_transaction_is_immutable(transaction: CreditTransaction) -> None:
    with pytest.raises(FrozenInstanceError):
        transaction.subscription_delta = 500


def test_preserves_ids_and_timestamp() -> None:
    transaction_id = uuid4()
    credit_id = uuid4()
    reference_id = uuid4()
    timestamp = datetime.now(UTC)

    transaction = CreditTransaction(
        id=transaction_id,
        credit_id=credit_id,
        reference_id=reference_id,
        user_id="user-301",
        transaction_type=CreditTransactionType.TOP_UP_PURCHASED,
        subscription_delta=0,
        top_up_delta=500,
        subscription_balance_after=0,
        top_up_balance_after=500,
        created_at=timestamp,
    )

    assert transaction.id == transaction_id
    assert transaction.credit_id == credit_id
    assert transaction.reference_id == reference_id
    assert transaction.created_at == timestamp


def test_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        CreditTransaction(
            user_id="user-301",
            transaction_type=CreditTransactionType.ADJUSTMENT,
            subscription_delta=1,
            top_up_delta=0,
            subscription_balance_after=1,
            top_up_balance_after=0,
            created_at=datetime(2026, 1, 1),
        )
