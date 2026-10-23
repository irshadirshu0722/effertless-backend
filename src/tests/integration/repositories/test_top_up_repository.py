"""Integration tests for PostgresTopUpRepository."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.top_up import TopUp

pytestmark = pytest.mark.asyncio


async def test_save_and_get_by_id(top_up_repo) -> None:
    top_up = TopUp(
        user_id="user-201",
        seconds=3600,
        amount=Decimal("99.00"),
    )

    saved = await top_up_repo.save(top_up)
    fetched = await top_up_repo.get_by_id(saved.id)

    assert fetched is not None
    assert fetched.id == top_up.id
    assert fetched.user_id == "user-201"
    assert fetched.seconds == 3600
    assert fetched.amount == Decimal("99.00")


async def test_get_by_id_returns_none_when_missing(top_up_repo) -> None:
    assert await top_up_repo.get_by_id(uuid4()) is None


async def test_get_by_external_payment_id(top_up_repo) -> None:
    top_up = TopUp(
        user_id="user-202",
        seconds=3600,
        amount=Decimal("99.00"),
    )
    top_up.complete("payment-202")
    await top_up_repo.save(top_up)

    fetched = await top_up_repo.get_by_external_payment_id("payment-202")

    assert fetched is not None
    assert fetched.id == top_up.id


async def test_external_payment_id_returns_none_when_missing(
    top_up_repo,
) -> None:
    assert await top_up_repo.get_by_external_payment_id("missing-payment") is None


async def test_list_by_user_id(top_up_repo) -> None:
    await top_up_repo.save(TopUp(user_id="user-203", seconds=100, amount=Decimal("10")))
    await top_up_repo.save(TopUp(user_id="user-203", seconds=200, amount=Decimal("20")))
    await top_up_repo.save(TopUp(user_id="user-other", seconds=300, amount=Decimal("30")))

    result = await top_up_repo.list_by_user_id("user-203")

    assert len(result) == 2
    assert {item.user_id for item in result} == {"user-203"}
    assert {item.seconds for item in result} == {100, 200}


async def test_update_persists_completed_status(top_up_repo) -> None:
    top_up = await top_up_repo.save(TopUp(user_id="user-204", seconds=500, amount=Decimal("25")))

    top_up.complete("payment-204")
    updated = await top_up_repo.update(top_up)

    assert updated.status.value == "COMPLETED"
    assert updated.external_payment_id == "payment-204"
    assert updated.completed_at is not None


async def test_update_raises_when_top_up_does_not_exist(
    top_up_repo,
) -> None:
    top_up = TopUp(
        user_id="user-missing",
        seconds=100,
        amount=Decimal("10"),
    )
    top_up.id = uuid4()

    with pytest.raises(ValueError, match="not found"):
        await top_up_repo.update(top_up)
