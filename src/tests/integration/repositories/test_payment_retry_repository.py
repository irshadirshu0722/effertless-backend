from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities.payment_retry import (
    PaymentRetry,
    PaymentRetryStatus,
)
from tests.factories.make_subscription import make_subscription_data

pytestmark = pytest.mark.asyncio


async def test_save_persists_payment_retry(
    payment_retry_repo,
    subscription_repo,
):
    subscription = await subscription_repo.save(make_subscription_data())

    now = datetime.now(UTC)
    retry = PaymentRetry.create(
        subscription_id=subscription.id,
        billing_period_start=now,
        next_retry_at=now + timedelta(hours=1),
    )

    saved = await payment_retry_repo.save(retry)

    assert saved.id == retry.id
    assert saved.subscription_id == subscription.id
    assert saved.retry_count == 0
    assert saved.max_retries == 3
    assert saved.status is PaymentRetryStatus.SCHEDULED
    assert saved.next_retry_at == retry.next_retry_at


async def test_get_by_id_returns_none_for_missing_retry(
    payment_retry_repo,
):
    from uuid import uuid4

    assert await payment_retry_repo.get_by_id(uuid4()) is None


async def test_get_by_id_returns_saved_retry(
    payment_retry_repo,
    subscription_repo,
):
    subscription = await subscription_repo.save(make_subscription_data())
    now = datetime.now(UTC)

    retry = PaymentRetry.create(
        subscription_id=subscription.id,
        billing_period_start=now,
        next_retry_at=now + timedelta(hours=1),
    )
    saved = await payment_retry_repo.save(retry)

    result = await payment_retry_repo.get_by_id(saved.id)

    assert result is not None
    assert result.id == saved.id
    assert result.subscription_id == subscription.id


async def test_get_by_subscription_and_period_returns_retry(
    payment_retry_repo,
    subscription_repo,
):
    subscription = await subscription_repo.save(make_subscription_data())
    now = datetime.now(UTC)

    retry = PaymentRetry.create(
        subscription_id=subscription.id,
        billing_period_start=now,
        next_retry_at=now + timedelta(hours=1),
    )
    await payment_retry_repo.save(retry)

    result = await payment_retry_repo.get_by_subscription_and_period(
        subscription.id,
        now,
    )

    assert result is not None
    assert result.id == retry.id


async def test_get_by_subscription_and_period_returns_none_when_missing(
    payment_retry_repo,
    subscription_repo,
):
    subscription = await subscription_repo.save(make_subscription_data())

    result = await payment_retry_repo.get_by_subscription_and_period(
        subscription.id,
        datetime.now(UTC),
    )

    assert result is None


async def test_save_updates_existing_retry(
    payment_retry_repo,
    subscription_repo,
):
    subscription = await subscription_repo.save(make_subscription_data())
    now = datetime.now(UTC)

    retry = PaymentRetry.create(
        subscription_id=subscription.id,
        billing_period_start=now,
        next_retry_at=now + timedelta(hours=1),
    )
    saved = await payment_retry_repo.save(retry)

    saved.start_attempt()
    saved.record_failure(
        error="Payment declined",
        next_retry_at=now + timedelta(hours=6),
        payment_attempt_id="payment-attempt-001",
    )

    updated = await payment_retry_repo.save(saved)

    assert updated.id == retry.id
    assert updated.retry_count == 1
    assert updated.status is PaymentRetryStatus.SCHEDULED
    assert updated.last_error == "Payment declined"
    assert updated.last_payment_attempt_id == "payment-attempt-001"


async def test_list_due_returns_only_due_scheduled_retries(
    payment_retry_repo,
    subscription_repo,
):
    subscription = await subscription_repo.save(make_subscription_data())
    now = datetime.now(UTC)

    due = PaymentRetry.create(
        subscription_id=subscription.id,
        billing_period_start=now,
        next_retry_at=now - timedelta(minutes=5),
    )
    future = PaymentRetry.create(
        subscription_id=subscription.id,
        billing_period_start=now + timedelta(seconds=1),
        next_retry_at=now + timedelta(hours=1),
    )

    await payment_retry_repo.save(due)
    await payment_retry_repo.save(future)

    results = await payment_retry_repo.list_due(now=now)

    result_ids = {retry.id for retry in results}
    assert due.id in result_ids
    assert future.id not in result_ids


async def test_list_due_excludes_cancelled_retry(
    payment_retry_repo,
    subscription_repo,
):
    subscription = await subscription_repo.save(make_subscription_data())
    now = datetime.now(UTC)

    retry = PaymentRetry.create(
        subscription_id=subscription.id,
        billing_period_start=now,
        next_retry_at=now - timedelta(minutes=1),
    )
    retry.cancel()
    await payment_retry_repo.save(retry)

    results = await payment_retry_repo.list_due(now=now)

    assert all(item.id != retry.id for item in results)


async def test_list_due_rejects_invalid_limit(payment_retry_repo):
    with pytest.raises(ValueError, match="limit must be at least 1"):
        await payment_retry_repo.list_due(
            now=datetime.now(UTC),
            limit=0,
        )
