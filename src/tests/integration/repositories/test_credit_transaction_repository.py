"""Integration tests for PostgresCreditTransactionRepository."""

from uuid import uuid4

import pytest

from app.domain.entities.credit_transaction import (
    CreditTransaction,
    CreditTransactionType,
)

pytestmark = pytest.mark.asyncio


def make_transaction(
    *,
    user_id: str = "user-401",
    credit_id=None,
    subscription_delta: int = 100,
    top_up_delta: int = 0,
    subscription_balance_after: int = 100,
    top_up_balance_after: int = 0,
) -> CreditTransaction:
    return CreditTransaction(
        user_id=user_id,
        credit_id=credit_id,
        transaction_type=CreditTransactionType.ADJUSTMENT,
        subscription_delta=subscription_delta,
        top_up_delta=top_up_delta,
        subscription_balance_after=subscription_balance_after,
        top_up_balance_after=top_up_balance_after,
    )


async def test_create_and_get_by_id(
    credit_transaction_repo,
    credit_repo,
) -> None:
    credit = await credit_repo.save(
        __import__(
            "app.domain.entities.credit",
            fromlist=["Credit"],
        ).Credit(user_id="user-401")
    )

    transaction = make_transaction(credit_id=credit.id)
    saved = await credit_transaction_repo.create(transaction)

    fetched = await credit_transaction_repo.get_by_id(saved.id)

    assert fetched is not None
    assert fetched.id == transaction.id
    assert fetched.user_id == "user-401"
    assert fetched.credit_id == credit.id
    assert fetched.subscription_delta == 100
    assert fetched.subscription_balance_after == 100


async def test_get_by_id_returns_none_when_missing(
    credit_transaction_repo,
) -> None:
    assert await credit_transaction_repo.get_by_id(uuid4()) is None


async def test_list_by_user_id(
    credit_transaction_repo,
) -> None:
    await credit_transaction_repo.create(
        make_transaction(
            user_id="user-402",
            subscription_delta=100,
            subscription_balance_after=100,
        )
    )
    await credit_transaction_repo.create(
        make_transaction(
            user_id="user-402",
            subscription_delta=-25,
            subscription_balance_after=75,
        )
    )
    await credit_transaction_repo.create(
        make_transaction(
            user_id="user-other",
            subscription_delta=50,
            subscription_balance_after=50,
        )
    )

    result = await credit_transaction_repo.list_by_user_id("user-402")

    assert len(result) == 2
    assert all(item.user_id == "user-402" for item in result)


async def test_list_by_user_id_supports_pagination(
    credit_transaction_repo,
) -> None:
    for index in range(3):
        await credit_transaction_repo.create(
            make_transaction(
                user_id="user-403",
                subscription_delta=10,
                subscription_balance_after=(index + 1) * 10,
            )
        )

    first_page = await credit_transaction_repo.list_by_user_id(
        "user-403",
        limit=2,
        offset=0,
    )
    second_page = await credit_transaction_repo.list_by_user_id(
        "user-403",
        limit=2,
        offset=2,
    )

    assert len(first_page) == 2
    assert len(second_page) == 1
    assert first_page[0].id != second_page[0].id


async def test_list_by_credit_id(
    credit_transaction_repo,
    credit_repo,
) -> None:
    from app.domain.entities.credit import Credit

    credit = await credit_repo.save(Credit(user_id="user-404"))
    credit2 = await credit_repo.save(Credit(user_id="user-402"))
    await credit_transaction_repo.create(
        make_transaction(
            user_id="user-404",
            credit_id=credit.id,
        )
    )
    await credit_transaction_repo.create(
        make_transaction(
            user_id="user-404",
            credit_id=credit2.id,
        )
    )

    result = await credit_transaction_repo.list_by_credit_id(credit.id)

    assert len(result) == 1
    assert result[0].credit_id == credit.id


@pytest.mark.parametrize(
    ("limit", "offset"),
    [
        (0, 0),
        (-1, 0),
        (True, 0),
        (10, -1),
        (10, True),
    ],
)
async def test_rejects_invalid_pagination(
    credit_transaction_repo,
    limit: int,
    offset: int,
) -> None:
    with pytest.raises(ValueError):
        await credit_transaction_repo.list_by_user_id(
            "user-405",
            limit=limit,
            offset=offset,
        )
