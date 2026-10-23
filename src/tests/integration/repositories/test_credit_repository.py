"""Integration tests for PostgresCreditRepository."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import DatabaseError

from app.domain.entities.credit import Credit

pytestmark = pytest.mark.asyncio


async def test_save_and_get_by_user_id(credit_repo) -> None:
    credit = Credit(
        user_id="user-101",
        subscription_seconds=300,
        top_up_seconds=100,
    )

    saved = await credit_repo.save(credit)
    result = await credit_repo.get_by_user_id("user-101")

    assert saved.id == credit.id
    assert result is not None
    assert result.user_id == "user-101"
    assert result.subscription_seconds == 300
    assert result.top_up_seconds == 100
    assert result.total_seconds == 400


async def test_get_by_user_id_returns_none_when_missing(
    credit_repo,
) -> None:
    assert await credit_repo.get_by_user_id("missing-user") is None


async def test_get_by_id_returns_none_when_missing(credit_repo) -> None:
    assert await credit_repo.get_by_id(uuid4()) is None


async def test_save_updates_existing_credit(credit_repo) -> None:
    credit = await credit_repo.save(Credit(user_id="user-102"))

    credit.grant_subscription(500)
    credit.grant_top_up(200)

    updated = await credit_repo.save(credit)
    fetched = await credit_repo.get_by_user_id("user-102")

    assert updated.id == credit.id
    assert fetched is not None
    assert fetched.subscription_seconds == 500
    assert fetched.top_up_seconds == 200


async def test_update_persists_balance_changes(credit_repo) -> None:
    credit = await credit_repo.save(
        Credit(
            user_id="user-103",
            subscription_seconds=100,
            top_up_seconds=50,
        )
    )

    credit.consume(120)
    updated = await credit_repo.update(credit)

    assert updated.subscription_seconds == 0
    assert updated.top_up_seconds == 30


async def test_update_raises_when_credit_does_not_exist(
    credit_repo,
) -> None:
    credit = Credit(user_id="missing-user")

    with pytest.raises(ValueError, match="not found"):
        await credit_repo.update(credit)


async def test_save_rejects_duplicate_user_id(credit_repo) -> None:
    await credit_repo.save(Credit(user_id="user-duplicate"))

    with pytest.raises(DatabaseError):
        await credit_repo.save(Credit(user_id="user-duplicate"))
