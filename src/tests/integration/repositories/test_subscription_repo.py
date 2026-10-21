"""Integration tests for PostgresSubscriptionRepository."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.subscription import (
    SubscriptionOperationType,
    SubscriptionStatus,
)
from tests.factories import make_subscription_data

pytestmark = pytest.mark.asyncio


async def test_save_persists_subscription(subscription_repo) -> None:
    subscription = make_subscription_data(
        status=SubscriptionStatus.PENDING,
        external_subscription_id="cf-sub-001",
    )

    saved = await subscription_repo.save(subscription)

    assert saved.id == subscription.id
    assert saved.user_id == "user-123"
    assert saved.status is SubscriptionStatus.PENDING
    assert saved.external_subscription_id == "cf-sub-001"
    assert saved.snapshot_max_seconds == 120
    assert saved.snapshot_max_usage_per_day == 100
    assert saved.snapshot_price == Decimal("20.00")


async def test_save_updates_existing_subscription(
    subscription_repo,
) -> None:
    subscription = await subscription_repo.save(
        make_subscription_data(
            external_subscription_id="cf-sub-update",
        )
    )

    subscription.status = SubscriptionStatus.ACTIVE
    subscription.is_active = True
    subscription.operation_type = SubscriptionOperationType.UPGRADE

    updated = await subscription_repo.save(subscription)

    assert updated.id == subscription.id
    assert updated.status is SubscriptionStatus.ACTIVE
    assert updated.is_active is True
    assert updated.operation_type is SubscriptionOperationType.UPGRADE


async def test_save_rejects_incomplete_snapshot(
    subscription_repo,
) -> None:
    subscription = make_subscription_data(snapshot_max_seconds=None)

    with pytest.raises(ValueError, match="complete plan snapshot"):
        await subscription_repo.save(subscription)


async def test_get_by_id_returns_subscription(
    subscription_repo,
) -> None:
    saved = await subscription_repo.save(make_subscription_data())

    result = await subscription_repo.get_by_id(saved.id)

    assert result is not None
    assert result.id == saved.id
    assert result.user_id == saved.user_id


async def test_get_by_id_returns_none_for_missing_subscription(
    subscription_repo,
) -> None:
    assert await subscription_repo.get_by_id(uuid4()) is None


async def test_get_by_external_id_returns_subscription(
    subscription_repo,
) -> None:
    saved = await subscription_repo.save(
        make_subscription_data(
            external_subscription_id="cf-external-123",
        )
    )

    result = await subscription_repo.get_by_external_id("cf-external-123")

    assert result is not None
    assert result.id == saved.id


async def test_get_by_external_id_returns_none_when_missing(
    subscription_repo,
) -> None:
    assert await subscription_repo.get_by_external_id("unknown-external-id") is None


async def test_get_active_by_user_id_returns_active_subscription(
    subscription_repo,
) -> None:
    await subscription_repo.save(
        make_subscription_data(
            user_id="user-123",
            status=SubscriptionStatus.PENDING,
            is_active=False,
        )
    )

    active = await subscription_repo.save(
        make_subscription_data(
            user_id="user-123",
            status=SubscriptionStatus.ACTIVE,
            is_active=True,
            external_subscription_id="cf-active-123",
        )
    )

    result = await subscription_repo.get_active_by_user_id("user-123")

    assert result is not None
    assert result.id == active.id
    assert result.status is SubscriptionStatus.ACTIVE


async def test_get_active_by_user_id_returns_none_when_no_active_record(
    subscription_repo,
) -> None:
    await subscription_repo.save(
        make_subscription_data(
            user_id="user-123",
            status=SubscriptionStatus.PENDING,
            is_active=False,
        )
    )

    assert await subscription_repo.get_active_by_user_id("user-123") is None


async def test_get_latest_by_user_id_returns_latest_period_end(
    subscription_repo,
) -> None:
    now = datetime.now(UTC)

    older = await subscription_repo.save(
        make_subscription_data(
            user_id="user-123",
            current_period_start=now,
            current_period_end=now + timedelta(days=10),
        )
    )

    latest = await subscription_repo.save(
        make_subscription_data(
            user_id="user-123",
            current_period_start=now,
            current_period_end=now + timedelta(days=60),
        )
    )

    result = await subscription_repo.get_latest_by_user_id("user-123")

    assert result is not None
    assert result.id == latest.id
    assert result.id != older.id


async def test_get_latest_by_user_id_returns_none_for_unknown_user(
    subscription_repo,
) -> None:
    assert await subscription_repo.get_latest_by_user_id("unknown-user") is None


async def test_list_all_returns_subscriptions_and_total(
    subscription_repo,
) -> None:
    await subscription_repo.save(make_subscription_data(user_id="user-a"))
    await subscription_repo.save(make_subscription_data(user_id="user-b"))
    await subscription_repo.save(make_subscription_data(user_id="user-c"))

    subscriptions, total = await subscription_repo.list_all()

    assert total == 3
    assert len(subscriptions) == 3


async def test_list_all_filters_by_user_id(
    subscription_repo,
) -> None:
    await subscription_repo.save(make_subscription_data(user_id="user-a"))
    await subscription_repo.save(make_subscription_data(user_id="user-b"))
    await subscription_repo.save(make_subscription_data(user_id="user-a"))

    subscriptions, total = await subscription_repo.list_all(user_id="user-a")

    assert total == 2
    assert all(sub.user_id == "user-a" for sub in subscriptions)


async def test_list_all_filters_by_status(
    subscription_repo,
) -> None:
    await subscription_repo.save(
        make_subscription_data(
            status=SubscriptionStatus.ACTIVE,
            is_active=True,
        )
    )
    await subscription_repo.save(
        make_subscription_data(
            status=SubscriptionStatus.PENDING,
            is_active=False,
        )
    )

    subscriptions, total = await subscription_repo.list_all(status=SubscriptionStatus.ACTIVE.value)

    assert total == 1
    assert subscriptions[0].status is SubscriptionStatus.ACTIVE


async def test_list_all_filters_by_user_and_status(
    subscription_repo,
) -> None:
    await subscription_repo.save(
        make_subscription_data(
            user_id="user-a",
            status=SubscriptionStatus.ACTIVE,
            is_active=True,
        )
    )
    await subscription_repo.save(
        make_subscription_data(
            user_id="user-a",
            status=SubscriptionStatus.PENDING,
        )
    )
    await subscription_repo.save(
        make_subscription_data(
            user_id="user-b",
            status=SubscriptionStatus.ACTIVE,
            is_active=True,
        )
    )

    subscriptions, total = await subscription_repo.list_all(
        user_id="user-a",
        status=SubscriptionStatus.ACTIVE.value,
    )

    assert total == 1
    assert subscriptions[0].user_id == "user-a"
    assert subscriptions[0].status is SubscriptionStatus.ACTIVE


async def test_list_all_applies_pagination(
    subscription_repo,
) -> None:
    now = datetime.now(UTC)

    for index in range(3):
        await subscription_repo.save(
            make_subscription_data(
                user_id=f"user-{index}",
                created_at=now + timedelta(seconds=index),
                updated_at=now + timedelta(seconds=index),
            )
        )

    subscriptions, total = await subscription_repo.list_all(
        limit=2,
        offset=0,
    )

    assert total == 3
    assert len(subscriptions) == 2
    assert subscriptions[0].user_id == "user-0"
    assert subscriptions[1].user_id == "user-1"

    next_page, next_total = await subscription_repo.list_all(
        limit=2,
        offset=2,
    )

    assert next_total == 3
    assert len(next_page) == 1
    assert next_page[0].user_id == "user-2"


async def test_get_status_counts(subscription_repo) -> None:
    await subscription_repo.save(
        make_subscription_data(
            status=SubscriptionStatus.ACTIVE,
            is_active=True,
        )
    )
    await subscription_repo.save(
        make_subscription_data(
            status=SubscriptionStatus.ACTIVE,
            is_active=True,
        )
    )
    await subscription_repo.save(make_subscription_data(status=SubscriptionStatus.PENDING))

    counts = await subscription_repo.get_status_counts()

    assert counts["ACTIVE"] == 2
    assert counts["PENDING"] == 1


async def test_get_by_field_filters(subscription_repo) -> None:
    saved = await subscription_repo.save(
        make_subscription_data(
            external_subscription_id="cf-filter-123",
            status=SubscriptionStatus.PENDING,
        )
    )

    result = await subscription_repo.get(
        external_subscription_id="cf-filter-123",
        status=SubscriptionStatus.PENDING.value,
    )

    assert result is not None
    assert result.id == saved.id


async def test_get_supports_null_filter(subscription_repo) -> None:
    saved = await subscription_repo.save(make_subscription_data(external_subscription_id=None))

    result = await subscription_repo.get(
        external_subscription_id=None,
        id=saved.id,
    )

    assert result is not None
    assert result.id == saved.id


async def test_get_rejects_invalid_filter_field(
    subscription_repo,
) -> None:
    with pytest.raises(
        ValueError,
        match="Invalid subscription filter field",
    ):
        await subscription_repo.get(not_a_column="value")


async def test_get_returns_none_when_no_record_matches(
    subscription_repo,
) -> None:
    result = await subscription_repo.get(user_id="unknown-user")

    assert result is None


@pytest.mark.asyncio
async def test_has_user_used_trial_returns_false_when_no_trial_exists(
    subscription_repo,
):
    result = await subscription_repo.has_user_used_trial("new-user")

    assert result is False


@pytest.mark.asyncio
async def test_has_user_used_trial_returns_true_when_trial_exists(
    subscription_repo,
):
    now = datetime.now(UTC)

    trial_subscription = make_subscription_data(
        has_trial=True,
        trial_start=now,
        trial_end=now + timedelta(days=7),
    )
    await subscription_repo.save(trial_subscription)

    result = await subscription_repo.has_user_used_trial(trial_subscription.user_id)

    assert result is True


@pytest.mark.asyncio
async def test_has_user_used_trial_ignores_other_users(
    subscription_repo,
):
    now = datetime.now(UTC)

    trial_subscription = make_subscription_data(
        has_trial=True,
        trial_start=now,
        trial_end=now + timedelta(days=7),
    )
    await subscription_repo.save(trial_subscription)

    result = await subscription_repo.has_user_used_trial("another-user")

    assert result is False


@pytest.mark.asyncio
async def test_subscription_trial_fields_round_trip(subscription_repo):
    now = datetime.now(UTC)

    subscription = make_subscription_data(
        has_trial=True,
        trial_start=now,
        trial_end=now + timedelta(days=7),
    )

    saved = await subscription_repo.save(subscription)
    retrieved = await subscription_repo.get_by_id(saved.id)

    assert retrieved is not None
    assert retrieved.has_trial is True
    assert retrieved.trial_start == now
    assert retrieved.trial_end == now + timedelta(days=7)
