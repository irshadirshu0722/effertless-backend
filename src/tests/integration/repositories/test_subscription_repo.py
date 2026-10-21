from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities.subscription import (
    SubscriptionStatus,
)
from tests.factories import make_subscription_data


@pytest.fixture
def subscription_factory(created_plan):
    def factory(**overrides):
        defaults = {
            "user_id": "user-123",
            "plan_id": created_plan.id,
            "status": SubscriptionStatus.PENDING,
            "is_active": False,
            "external_subscription_id": f"cf-{uuid4()}",
            "current_period_start": datetime.now(UTC),
            "current_period_end": datetime.now(UTC) + timedelta(days=30),
        }
        defaults.update(overrides)
        return make_subscription_data(**defaults)

    return factory


async def persist(subscription_repo, *subscriptions):
    """Persist domain entities using the repository."""
    return [await subscription_repo.save(subscription) for subscription in subscriptions]


# ---------------------------------------------------------
# get_active_by_user_id()
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_active_by_user_id_returns_active_subscription(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory(
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
    )
    await persist(subscription_repo, subscription)

    result = await subscription_repo.get_active_by_user_id("user-123")

    assert result is not None
    assert result.id == subscription.id
    assert result.user_id == "user-123"
    assert result.status == SubscriptionStatus.ACTIVE
    assert result.is_active is True


@pytest.mark.asyncio
async def test_get_active_by_user_id_returns_none_when_inactive(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory(is_active=False)
    await persist(subscription_repo, subscription)

    result = await subscription_repo.get_active_by_user_id("user-123")

    assert result is None


@pytest.mark.asyncio
async def test_get_active_by_user_id_does_not_return_another_user(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory(
        user_id="user-456",
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
    )
    await persist(subscription_repo, subscription)

    result = await subscription_repo.get_active_by_user_id("user-123")

    assert result is None


# ---------------------------------------------------------
# get_latest_by_user_id()
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_latest_by_user_id_returns_latest_period_end(
    subscription_repo,
    subscription_factory,
):
    now = datetime.now(UTC)

    older = subscription_factory(
        current_period_end=now + timedelta(days=10),
    )
    newer = subscription_factory(
        current_period_end=now + timedelta(days=30),
    )
    await persist(subscription_repo, older, newer)

    result = await subscription_repo.get_latest_by_user_id("user-123")

    assert result is not None
    assert result.id == newer.id


@pytest.mark.asyncio
async def test_get_latest_by_user_id_returns_none_when_missing(
    subscription_repo,
):
    result = await subscription_repo.get_latest_by_user_id("missing-user")

    assert result is None


# ---------------------------------------------------------
# get_by_id()
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_returns_subscription(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory()
    await persist(subscription_repo, subscription)

    result = await subscription_repo.get_by_id(subscription.id)

    assert result is not None
    assert result.id == subscription.id


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(subscription_repo):
    result = await subscription_repo.get_by_id(uuid4())

    assert result is None


# ---------------------------------------------------------
# get_by_external_id()
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_external_id_returns_subscription(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory(
        external_subscription_id="cf-external-123",
    )
    await persist(subscription_repo, subscription)

    result = await subscription_repo.get_by_external_id("cf-external-123")

    assert result is not None
    assert result.id == subscription.id
    assert result.external_subscription_id == "cf-external-123"


@pytest.mark.asyncio
async def test_get_by_external_id_returns_none_when_missing(
    subscription_repo,
):
    result = await subscription_repo.get_by_external_id("missing-external-id")

    assert result is None


# ---------------------------------------------------------
# list_all()
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_list_all_returns_entities_and_total_count(
    subscription_repo,
    subscription_factory,
):
    subscriptions = [subscription_factory(user_id=f"user-{i}") for i in range(3)]
    await persist(subscription_repo, *subscriptions)

    results, total = await subscription_repo.list_all()

    assert total == 3
    assert len(results) == 3
    assert {item.id for item in results} == {item.id for item in subscriptions}


@pytest.mark.asyncio
async def test_list_all_filters_by_user_id(
    subscription_repo,
    subscription_factory,
):
    subscriptions = [
        subscription_factory(user_id="user-123"),
        subscription_factory(user_id="user-123"),
        subscription_factory(user_id="user-456"),
    ]
    await persist(subscription_repo, *subscriptions)

    results, total = await subscription_repo.list_all(user_id="user-123")

    assert total == 2
    assert len(results) == 2
    assert all(item.user_id == "user-123" for item in results)


@pytest.mark.asyncio
async def test_list_all_filters_by_status(
    subscription_repo,
    subscription_factory,
):
    subscriptions = [
        subscription_factory(status=SubscriptionStatus.PENDING),
        subscription_factory(status=SubscriptionStatus.PENDING),
        subscription_factory(status=SubscriptionStatus.ACTIVE),
    ]
    await persist(subscription_repo, *subscriptions)

    results, total = await subscription_repo.list_all(
        status=SubscriptionStatus.PENDING.value,
    )

    assert total == 2
    assert len(results) == 2
    assert all(item.status == SubscriptionStatus.PENDING for item in results)


@pytest.mark.asyncio
async def test_list_all_combines_filters(
    subscription_repo,
    subscription_factory,
):
    subscriptions = [
        subscription_factory(
            user_id="user-123",
            status=SubscriptionStatus.PENDING,
        ),
        subscription_factory(
            user_id="user-123",
            status=SubscriptionStatus.ACTIVE,
        ),
        subscription_factory(
            user_id="user-456",
            status=SubscriptionStatus.PENDING,
        ),
    ]
    await persist(subscription_repo, *subscriptions)

    results, total = await subscription_repo.list_all(
        user_id="user-123",
        status=SubscriptionStatus.PENDING.value,
    )

    assert total == 1
    assert len(results) == 1
    assert results[0].user_id == "user-123"
    assert results[0].status == SubscriptionStatus.PENDING


@pytest.mark.asyncio
async def test_list_all_applies_limit_and_offset(
    subscription_repo,
    subscription_factory,
):
    subscriptions = [subscription_factory(user_id=f"user-{i}") for i in range(5)]
    await persist(subscription_repo, *subscriptions)

    results, total = await subscription_repo.list_all(limit=2, offset=1)

    assert total == 5
    assert len(results) == 2


# ---------------------------------------------------------
# get_status_counts()
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status_counts_returns_counts_by_status(
    subscription_repo,
    subscription_factory,
):
    subscriptions = [
        subscription_factory(status=SubscriptionStatus.PENDING),
        subscription_factory(status=SubscriptionStatus.PENDING),
        subscription_factory(status=SubscriptionStatus.ACTIVE),
    ]
    await persist(subscription_repo, *subscriptions)

    counts = await subscription_repo.get_status_counts()

    assert counts == {
        SubscriptionStatus.PENDING.value: 2,
        SubscriptionStatus.ACTIVE.value: 1,
    }


@pytest.mark.asyncio
async def test_get_status_counts_returns_empty_dict(
    subscription_repo,
):
    counts = await subscription_repo.get_status_counts()

    assert counts == {}


# ---------------------------------------------------------
# save()
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_save_persists_domain_entity(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory(
        external_subscription_id="cf-save-123",
        status=SubscriptionStatus.PENDING,
    )

    saved = await subscription_repo.save(subscription)

    assert saved.id == subscription.id
    assert saved.user_id == subscription.user_id
    assert saved.status == SubscriptionStatus.PENDING
    assert saved.external_subscription_id == "cf-save-123"

    loaded = await subscription_repo.get_by_id(subscription.id)

    assert loaded is not None
    assert loaded.id == subscription.id


@pytest.mark.asyncio
async def test_save_updates_existing_subscription(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory(
        external_customer_id="customer-original",
    )
    await subscription_repo.save(subscription)

    updated = replace(
        subscription,
        external_customer_id="customer-updated",
    )
    saved = await subscription_repo.save(updated)

    assert saved.id == subscription.id
    assert saved.external_customer_id == "customer-updated"

    loaded = await subscription_repo.get_by_id(subscription.id)

    assert loaded is not None
    assert loaded.external_customer_id == "customer-updated"


# ---------------------------------------------------------
# get()
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_filters_by_user_id(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory(user_id="user-123")
    await persist(subscription_repo, subscription)

    result = await subscription_repo.get(user_id="user-123")

    assert result is not None
    assert result.id == subscription.id


@pytest.mark.asyncio
async def test_get_supports_none_filter(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory(external_customer_id=None)
    await persist(subscription_repo, subscription)

    result = await subscription_repo.get(
        id=subscription.id,
        external_customer_id=None,
    )

    assert result is not None
    assert result.id == subscription.id
    assert result.external_customer_id is None


@pytest.mark.asyncio
async def test_get_raises_for_invalid_filter(subscription_repo):
    with pytest.raises(
        ValueError,
        match="Invalid subscription filter field: unknown_field",
    ):
        await subscription_repo.get(unknown_field="value")


@pytest.mark.asyncio
async def test_get_returns_none_when_filter_does_not_match(
    subscription_repo,
    subscription_factory,
):
    subscription = subscription_factory(user_id="user-123")
    await persist(subscription_repo, subscription)

    result = await subscription_repo.get(user_id="missing-user")

    assert result is None
