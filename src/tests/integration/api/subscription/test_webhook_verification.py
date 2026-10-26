import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.domain.entities.plan import PlanCode
from app.domain.entities.subscription import (
    ReplacementStrategy,
    SubscriptionOperationType,
    SubscriptionStatus,
)
from tests.factories.make_subscription import make_subscription_data

pytestmark = pytest.mark.asyncio


def make_subscription(*, plan_id, **overrides):
    """Build subscription data using a real persisted plan UUID."""
    now = datetime.now(UTC)

    data = {
        "id": uuid4(),
        "user_id": "user-123",
        "plan_id": plan_id,
        "status": SubscriptionStatus.PENDING,
        "is_active": False,
        "provider": "cashfree",
        "external_subscription_id": f"cf-sub-{uuid4()}",
        "external_customer_id": None,
        "current_period_start": now - timedelta(days=5),
        "current_period_end": now + timedelta(days=25),
        "cancelled_at": None,
        "operation_type": SubscriptionOperationType.NEW,
        "related_subscription_id": None,
        "replacement_strategy": ReplacementStrategy.IMMEDIATE,
        "snapshot_plan_name": "Pro",
        "snapshot_max_seconds": 3600,
        "snapshot_price": Decimal("20.00"),
        "snapshot_currency": "PLN",
        "has_trial": False,
        "trial_start": None,
        "trial_end": None,
    }

    data.update(overrides)
    return make_subscription_data(**data)


def webhook_payload(
    *,
    event_type: str,
    external_subscription_id: str,
    status: str | None = None,
):
    """Create a Cashfree-like webhook payload for integration tests."""
    subscription_details = {
        "subscription_id": external_subscription_id,
    }

    if status is not None:
        subscription_details["subscription_status"] = status

    return {
        "type": event_type,
        "data": {
            "subscription_details": subscription_details,
        },
    }


async def post_webhook(
    async_client: AsyncClient,
    payload: dict | str,
    *,
    signature: str = "test-signature",
    timestamp: str = "1720000000",
):
    content = json.dumps(payload) if isinstance(payload, dict) else payload

    return await async_client.post(
        "/api/v1/subscriptions/webhook",
        content=content,
        headers={
            "content-type": "application/json",
            "x-webhook-signature": signature,
            "x-webhook-timestamp": timestamp,
        },
    )


async def persist_subscription(subscription_repo, subscription):
    await subscription_repo.save(subscription)
    return subscription


async def test_active_webhook_activates_subscription(
    async_client,
    subscription_repo,
    create_all_plan,
    mock_cashfree_gateway,
):
    plan = create_all_plan[PlanCode.PRO]
    subscription = make_subscription(plan_id=plan.id)
    await persist_subscription(subscription_repo, subscription)

    payload = webhook_payload(
        event_type="SUBSCRIPTION_STATUS_CHANGED",
        external_subscription_id=subscription.external_subscription_id,
        status="ACTIVE",
    )

    response = await post_webhook(async_client, payload)

    assert response.status_code == 200
    assert response.json() == {"status": "acknowledged"}

    updated = await subscription_repo.get_by_id(subscription.id)
    assert updated.status == SubscriptionStatus.ACTIVE
    assert updated.is_active is True


async def test_customer_cancelled_period_end_keeps_access_until_period_end(
    async_client,
    subscription_repo,
    create_all_plan,
    mock_cashfree_gateway,
):
    plan = create_all_plan[PlanCode.PRO]
    period_end = datetime.now(UTC) + timedelta(days=5)

    subscription = make_subscription(
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
        current_period_end=period_end,
        replacement_strategy=ReplacementStrategy.PERIOD_END,
    )
    await persist_subscription(subscription_repo, subscription)

    payload = webhook_payload(
        event_type="SUBSCRIPTION_STATUS_CHANGED",
        external_subscription_id=subscription.external_subscription_id,
        status="CUSTOMER_CANCELLED",
    )

    response = await post_webhook(async_client, payload)

    assert response.status_code == 200

    updated = await subscription_repo.get_by_id(subscription.id)
    assert updated.is_active is True
    assert updated.current_period_end == period_end


async def test_cancelled_period_end_subscription_loses_access_after_period_end(
    async_client,
    subscription_repo,
    create_all_plan,
    mock_cashfree_gateway,
):
    plan = create_all_plan[PlanCode.PRO]
    period_end = datetime.now(UTC) - timedelta(days=1)

    subscription = make_subscription(
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
        current_period_end=period_end,
    )
    await persist_subscription(subscription_repo, subscription)

    payload = webhook_payload(
        event_type="SUBSCRIPTION_STATUS_CHANGED",
        external_subscription_id=subscription.external_subscription_id,
        status="CUSTOMER_CANCELLED",
    )

    response = await post_webhook(async_client, payload)

    assert response.status_code == 200

    updated = await subscription_repo.get_by_id(subscription.id)
    assert updated.is_active is False


async def test_immediate_replacement_cancels_old_subscription(
    async_client,
    subscription_repo,
    create_all_plan,
    mock_cashfree_gateway,
):
    plan = create_all_plan[PlanCode.PRO]

    old_subscription = make_subscription(
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
        replacement_strategy=None,
    )
    await persist_subscription(subscription_repo, old_subscription)

    new_subscription = make_subscription(
        plan_id=plan.id,
        status=SubscriptionStatus.PENDING,
        is_active=False,
        related_subscription_id=old_subscription.id,
        replacement_strategy=ReplacementStrategy.IMMEDIATE,
    )
    await persist_subscription(subscription_repo, new_subscription)

    payload = webhook_payload(
        event_type="SUBSCRIPTION_STATUS_CHANGED",
        external_subscription_id=new_subscription.external_subscription_id,
        status="ACTIVE",
    )

    response = await post_webhook(async_client, payload)

    assert response.status_code == 200

    updated_new = await subscription_repo.get_by_id(new_subscription.id)
    updated_old = await subscription_repo.get_by_id(old_subscription.id)

    assert updated_new.is_active is True
    assert updated_new.status == SubscriptionStatus.ACTIVE
    assert updated_old.is_active is False


async def test_period_end_replacement_does_not_cancel_old_subscription(
    async_client,
    subscription_repo,
    create_all_plan,
    mock_cashfree_gateway,
):
    plan = create_all_plan[PlanCode.PRO]

    old_subscription = make_subscription(
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
        replacement_strategy=None,
    )
    await persist_subscription(subscription_repo, old_subscription)

    new_subscription = make_subscription(
        plan_id=plan.id,
        status=SubscriptionStatus.PENDING,
        is_active=False,
        related_subscription_id=old_subscription.id,
        replacement_strategy=ReplacementStrategy.PERIOD_END,
    )
    await persist_subscription(subscription_repo, new_subscription)

    payload = webhook_payload(
        event_type="SUBSCRIPTION_STATUS_CHANGED",
        external_subscription_id=new_subscription.external_subscription_id,
        status="ACTIVE",
    )

    response = await post_webhook(async_client, payload)

    assert response.status_code == 200

    updated_old = await subscription_repo.get_by_id(old_subscription.id)
    assert updated_old.is_active is True


async def test_invalid_signature_is_rejected(
    async_client,
    subscription_repo,
    create_all_plan,
    mock_cashfree_gateway,
):
    plan = create_all_plan[PlanCode.PRO]
    subscription = make_subscription(plan_id=plan.id)
    await persist_subscription(subscription_repo, subscription)

    mock_cashfree_gateway.verify_webhook_signature.return_value = False

    payload = webhook_payload(
        event_type="SUBSCRIPTION_STATUS_CHANGED",
        external_subscription_id=subscription.external_subscription_id,
        status="ACTIVE",
    )

    response = await post_webhook(async_client, payload)

    assert response.status_code in (400, 401, 403)


async def test_duplicate_webhook_is_idempotent(
    async_client,
    subscription_repo,
    create_all_plan,
    mock_cashfree_gateway,
):
    plan = create_all_plan[PlanCode.PRO]
    subscription = make_subscription(plan_id=plan.id)
    await persist_subscription(subscription_repo, subscription)

    payload = webhook_payload(
        event_type="SUBSCRIPTION_STATUS_CHANGED",
        external_subscription_id=subscription.external_subscription_id,
        status="ACTIVE",
    )

    first_response = await post_webhook(async_client, payload)
    second_response = await post_webhook(async_client, payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    updated = await subscription_repo.get_by_id(subscription.id)
    assert updated.status == SubscriptionStatus.ACTIVE
    assert updated.is_active is True


async def test_unsupported_event_is_acknowledged_without_subscription_changes(
    async_client,
    subscription_repo,
    create_all_plan,
    mock_cashfree_gateway,
):
    plan = create_all_plan[PlanCode.PRO]
    subscription = make_subscription(plan_id=plan.id)
    await persist_subscription(subscription_repo, subscription)

    payload = webhook_payload(
        event_type="SOME_UNSUPPORTED_EVENT",
        external_subscription_id=subscription.external_subscription_id,
    )

    response = await post_webhook(async_client, payload)

    assert response.status_code == 200
    assert response.json() == {"status": "acknowledged"}

    updated = await subscription_repo.get_by_id(subscription.id)
    assert updated.status == SubscriptionStatus.PENDING
    assert updated.is_active is False


async def test_malformed_json_is_acknowledged_without_subscription_changes(
    async_client,
    subscription_repo,
    create_all_plan,
    mock_cashfree_gateway,
):
    plan = create_all_plan[PlanCode.PRO]
    subscription = make_subscription(plan_id=plan.id)
    await persist_subscription(subscription_repo, subscription)

    response = await post_webhook(async_client, "{invalid-json")

    assert response.status_code == 200
    assert response.json() == {"status": "acknowledged"}

    updated = await subscription_repo.get_by_id(subscription.id)
    assert updated.status == SubscriptionStatus.PENDING
    assert updated.is_active is False


async def test_unknown_subscription_is_not_recorded_as_processed(
    async_client,
    create_all_plan,
    mock_cashfree_gateway,
):
    payload = webhook_payload(
        event_type="SUBSCRIPTION_STATUS_CHANGED",
        external_subscription_id="unknown-cashfree-subscription",
        status="ACTIVE",
    )

    response = await post_webhook(async_client, payload)

    assert response.status_code == 404
