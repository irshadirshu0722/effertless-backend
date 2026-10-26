from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.use_case.subscription.command import (
    SubscriptionWebhookCommand,
)
from app.application.use_case.subscription.exceptions import (
    InvalidWebhookSignatureError,
)
from app.domain.entities.subscription import (
    ReplacementStrategy,
    SubscriptionOperationType,
    SubscriptionStatus,
)
from tests.factories import make_subscription_data


@pytest.fixture
def current_period_end():
    return datetime.now(UTC) + timedelta(days=20)


def make_subscription(
    *,
    status=SubscriptionStatus.PENDING,
    is_active=False,
    replacement_strategy=None,
    related_subscription_id=None,
    period_end=None,
    **overrides,
):
    now = datetime.now(UTC)

    data = {
        "id": uuid4(),
        "user_id": "user-123",
        "plan_id": "plan-123",
        "status": status,
        "is_active": is_active,
        "provider": "cashfree",
        "external_subscription_id": f"cf-sub-{uuid4()}",
        "external_customer_id": None,
        "current_period_start": now,
        "current_period_end": period_end or now + timedelta(days=20),
        "cancelled_at": None,
        "operation_type": SubscriptionOperationType.NEW,
        "related_subscription_id": related_subscription_id,
        "replacement_strategy": replacement_strategy,
        "snapshot_plan_name": "Pro",
        "snapshot_max_seconds": 3600,
        "snapshot_price": Decimal("20"),
        "snapshot_currency": "PLN",
        "created_at": now,
        "updated_at": now,
        "has_trial": False,
        "trial_start": None,
        "trial_end": None,
    }
    data.update(overrides)
    return make_subscription_data(**data)


def make_command(
    *,
    event_type="SUBSCRIPTION_STATUS_CHANGED",
    subscription_id="cf-sub-123",
    status="ACTIVE",
    event_id="event-123",
):
    event_data = {
        "type": event_type,
        "event_id": event_id,
        "event_time": datetime.now(UTC).isoformat(),
        "data": {
            "subscription_details": {
                "subscription_id": subscription_id,
                "subscription_status": status,
            }
        },
    }

    return SubscriptionWebhookCommand(
        raw_payload='{"test": "payload"}',
        signature="valid-signature",
        timestamp="timestamp",
        event_data=event_data,
    )


@pytest.mark.asyncio
async def test_rejects_invalid_signature(
    webhook_verification_service,
    payment_gateway,
    webhook_repo,
):
    payment_gateway.verify_webhook_signature.return_value = False
    command = make_command()

    with pytest.raises(InvalidWebhookSignatureError):
        await webhook_verification_service.execute(command)

    webhook_repo.has_been_processed.assert_not_awaited()


@pytest.mark.asyncio
async def test_ignores_duplicate_webhook(
    webhook_verification_service,
    payment_gateway,
    webhook_repo,
    subscription_repo,
):
    payment_gateway.verify_webhook_signature.return_value = True
    webhook_repo.has_been_processed.return_value = True

    result = await webhook_verification_service.execute(make_command())

    assert result is True
    subscription_repo.save.assert_not_awaited()
    webhook_repo.record_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_ignores_unsupported_event_type(
    webhook_verification_service,
    payment_gateway,
    webhook_repo,
    subscription_repo,
):
    payment_gateway.verify_webhook_signature.return_value = True
    webhook_repo.has_been_processed.return_value = False

    result = await webhook_verification_service.execute(make_command(event_type="SOME_OTHER_EVENT"))

    assert result is True
    subscription_repo.save.assert_not_awaited()
    webhook_repo.record_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_active_event_activates_subscription(
    webhook_verification_service,
    payment_gateway,
    webhook_repo,
    subscription_repo,
):
    incoming = make_subscription(
        status=SubscriptionStatus.PENDING,
        is_active=False,
    )

    payment_gateway.verify_webhook_signature.return_value = True
    webhook_repo.has_been_processed.return_value = False
    subscription_repo.get_by_external_id.return_value = incoming

    result = await webhook_verification_service.execute(
        make_command(
            subscription_id=incoming.external_subscription_id,
            status="ACTIVE",
        )
    )

    assert result is True
    assert incoming.status == SubscriptionStatus.ACTIVE
    assert incoming.is_active is True

    subscription_repo.save.assert_awaited_once_with(incoming)
    webhook_repo.record_event.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_active"),
    [
        ("PENDING", False),
        ("COMPLETED", False),
        ("EXPIRED", False),
        ("LINK_EXPIRED", False),
        ("CARD_EXPIRED", False),
    ],
)
async def test_terminal_or_pending_status_does_not_grant_access(
    webhook_verification_service,
    payment_gateway,
    webhook_repo,
    subscription_repo,
    status,
    expected_active,
):
    incoming = make_subscription(
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
    )

    payment_gateway.verify_webhook_signature.return_value = True
    webhook_repo.has_been_processed.return_value = False
    subscription_repo.get_by_external_id.return_value = incoming

    await webhook_verification_service.execute(
        make_command(
            subscription_id=incoming.external_subscription_id,
            status=status,
        )
    )

    assert incoming.status == SubscriptionStatus(status)
    assert incoming.is_active is expected_active


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "strategy", "period_days", "expected_active"),
    [
        (
            SubscriptionStatus.CUSTOMER_CANCELLED,
            ReplacementStrategy.PERIOD_END,
            10,
            True,
        ),
        (
            SubscriptionStatus.CANCELLED,
            ReplacementStrategy.PERIOD_END,
            10,
            True,
        ),
        (
            SubscriptionStatus.CUSTOMER_CANCELLED,
            ReplacementStrategy.IMMEDIATE,
            10,
            False,
        ),
        (
            SubscriptionStatus.CANCELLED,
            ReplacementStrategy.IMMEDIATE,
            10,
            False,
        ),
        (
            SubscriptionStatus.CUSTOMER_CANCELLED,
            ReplacementStrategy.PERIOD_END,
            -1,
            False,
        ),
    ],
)
async def test_calculates_access_for_cancelled_subscription(
    webhook_verification_service,
    status,
    strategy,
    period_days,
    expected_active,
):
    now = datetime.now(UTC)
    period_end = now + timedelta(days=period_days)

    result = webhook_verification_service._calculate_is_active(
        status=status,
        replacement_strategy=strategy,
        current_period_end=period_end,
        now=now,
    )

    assert result is expected_active


@pytest.mark.asyncio
async def test_immediate_replacement_cancels_previous_subscription(
    webhook_verification_service,
    payment_gateway,
    webhook_repo,
    subscription_repo,
):
    old_subscription = make_subscription(
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
    )
    new_subscription = make_subscription(
        status=SubscriptionStatus.PENDING,
        is_active=False,
        replacement_strategy=ReplacementStrategy.IMMEDIATE,
        related_subscription_id=old_subscription.id,
    )

    payment_gateway.verify_webhook_signature.return_value = True
    webhook_repo.has_been_processed.return_value = False

    subscription_repo.get_by_external_id.return_value = new_subscription
    subscription_repo.get_by_id.return_value = old_subscription

    await webhook_verification_service.execute(
        make_command(
            subscription_id=new_subscription.external_subscription_id,
            status="ACTIVE",
        )
    )

    payment_gateway.cancel_subscription.assert_awaited_once_with(
        old_subscription.external_subscription_id
    )
    assert old_subscription.status == SubscriptionStatus.CANCELLED
    assert new_subscription.status == SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_period_end_replacement_does_not_cancel_previous_subscription(
    webhook_verification_service,
    payment_gateway,
    webhook_repo,
    subscription_repo,
):
    old_subscription = make_subscription(
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
    )
    new_subscription = make_subscription(
        status=SubscriptionStatus.PENDING,
        is_active=False,
        replacement_strategy=ReplacementStrategy.PERIOD_END,
        related_subscription_id=old_subscription.id,
    )

    payment_gateway.verify_webhook_signature.return_value = True
    webhook_repo.has_been_processed.return_value = False

    subscription_repo.get_by_external_id.return_value = new_subscription
    subscription_repo.get_by_id.return_value = old_subscription

    await webhook_verification_service.execute(
        make_command(
            subscription_id=new_subscription.external_subscription_id,
            status="ACTIVE",
        )
    )

    payment_gateway.cancel_subscription.assert_not_awaited()
    assert old_subscription.status == SubscriptionStatus.ACTIVE
    assert new_subscription.status == SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_missing_subscription_raises_value_error(
    webhook_verification_service,
    payment_gateway,
    webhook_repo,
    subscription_repo,
):
    payment_gateway.verify_webhook_signature.return_value = True
    webhook_repo.has_been_processed.return_value = False
    subscription_repo.get_by_external_id.return_value = None

    with pytest.raises(ValueError, match="No local subscription found"):
        await webhook_verification_service.execute(make_command())

    webhook_repo.record_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_records_successfully_processed_webhook(
    webhook_verification_service,
    payment_gateway,
    webhook_repo,
    subscription_repo,
):
    incoming = make_subscription(
        status=SubscriptionStatus.PENDING,
        is_active=False,
    )

    payment_gateway.verify_webhook_signature.return_value = True
    webhook_repo.has_been_processed.return_value = False
    subscription_repo.get_by_external_id.return_value = incoming

    await webhook_verification_service.execute(
        make_command(
            subscription_id=incoming.external_subscription_id,
            status="ACTIVE",
            event_id="success-event",
        )
    )

    webhook_repo.record_event.assert_awaited_once()
    kwargs = webhook_repo.record_event.await_args.kwargs

    assert kwargs["event_id"] == "success-event"
    assert kwargs["event_type"] == "SUBSCRIPTION_STATUS_CHANGED"
    assert kwargs["status"] == "processed"
