from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_case.subscription import PlanNotFoundError
from app.application.use_case.subscription.command import InitiateCheckoutCommand
from app.core.exceptions import ActiveSubscriptionError
from app.domain.entities.subscription import (
    SubscriptionOperationType,
    SubscriptionStatus,
)


@pytest.fixture
def checkout_command(user):
    return InitiateCheckoutCommand(
        user=user,
        plan_code="pro",
        return_url="https://example.com/checkout/return",
    )


@pytest.fixture
def current_subscription():
    now = datetime.now(UTC)

    return SimpleNamespace(
        id="subscription-current",
        user_id="user-123",
        plan_id="plan-old",
        status=SubscriptionStatus.ACTIVE,
        cancelled_at=None,
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        snapshot=SimpleNamespace(price=Decimal("10.00")),
    )


@pytest.mark.asyncio
async def test_execute_creates_new_pending_subscription(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    checkout_command,
):
    plan_repo.get_by_code.return_value = active_plan

    result = await initiate_checkout_service.execute(checkout_command)

    assert result.subscription_id == "cashfree-sub-123"
    assert result.checkout_session_id == "checkout-session-123"
    assert result.status == "pending"

    plan_repo.get_by_code.assert_awaited_once_with("pro")
    subscription_repo.get_active_by_user_id.assert_awaited_once_with("user-123")

    payment_gateway.create_checkout_session.assert_awaited_once_with(
        user_id="user-123",
        user_email="user@example.com",
        plan=active_plan,
        return_url="https://example.com/checkout/return",
        first_charge_time=None,
    )

    subscription_repo.save.assert_awaited_once()

    saved_subscription = subscription_repo.save.await_args.args[0]

    assert saved_subscription.id is None
    assert saved_subscription.user_id == "user-123"
    assert saved_subscription.plan_id == "plan-123"
    assert saved_subscription.status == SubscriptionStatus.PENDING
    assert saved_subscription.provider == "cashfree"
    assert saved_subscription.external_subscription_id == "cashfree-sub-123"
    assert saved_subscription.operation_type == SubscriptionOperationType.NEW
    assert saved_subscription.related_subscription_id is None

    assert saved_subscription.snapshot.plan_name == "Pro"
    assert saved_subscription.snapshot.price == Decimal("20.00")
    assert saved_subscription.snapshot.currency == "PLN"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plan_changes",
    [
        {"is_active": False},
        {"is_deleted": True},
    ],
)
async def test_execute_rejects_inactive_or_deleted_plan(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    checkout_command,
    plan_changes,
):
    plan_data = vars(active_plan).copy()
    plan_data.update(plan_changes)
    plan = SimpleNamespace(**plan_data)
    plan_repo.get_by_code.return_value = plan

    with pytest.raises(PlanNotFoundError):
        await initiate_checkout_service.execute(checkout_command)

    subscription_repo.get_active_by_user_id.assert_not_awaited()
    payment_gateway.create_checkout_session.assert_not_awaited()
    subscription_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_rejects_missing_plan(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    checkout_command,
):
    plan_repo.get_by_code.return_value = None

    with pytest.raises(PlanNotFoundError):
        await initiate_checkout_service.execute(checkout_command)

    subscription_repo.get_active_by_user_id.assert_not_awaited()
    payment_gateway.create_checkout_session.assert_not_awaited()
    subscription_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_rejects_duplicate_active_subscription(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    checkout_command,
):
    current = SimpleNamespace(
        id="subscription-current",
        plan_id=active_plan.id,
        status=SubscriptionStatus.ACTIVE,
        cancelled_at=None,
        current_period_end=datetime.now(UTC) + timedelta(days=10),
        snapshot=SimpleNamespace(price=active_plan.offer_price),
    )

    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current

    with pytest.raises(ActiveSubscriptionError):
        await initiate_checkout_service.execute(checkout_command)

    payment_gateway.create_checkout_session.assert_not_awaited()
    subscription_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_starts_upgrade_immediately(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    checkout_command,
    current_subscription,
):
    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current_subscription

    result = await initiate_checkout_service.execute(checkout_command)

    payment_gateway.create_checkout_session.assert_awaited_once()
    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs

    assert gateway_kwargs["first_charge_time"] is None

    saved_subscription = subscription_repo.save.await_args.args[0]

    assert saved_subscription.operation_type == SubscriptionOperationType.UPGRADE
    assert saved_subscription.related_subscription_id == current_subscription.id
    assert saved_subscription.status == SubscriptionStatus.PENDING

    assert result.status == "pending"


@pytest.mark.asyncio
async def test_execute_schedules_downgrade_at_period_end(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    checkout_command,
    current_subscription,
):
    active_plan.offer_price = Decimal("5.00")
    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current_subscription

    await initiate_checkout_service.execute(checkout_command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved_subscription = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] == current_subscription.current_period_end
    assert saved_subscription.operation_type == SubscriptionOperationType.DOWNGRADE
    assert saved_subscription.current_period_start == current_subscription.current_period_end
    assert saved_subscription.related_subscription_id == current_subscription.id


@pytest.mark.asyncio
async def test_execute_schedules_same_price_different_plan_as_renewal(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    checkout_command,
    current_subscription,
):
    active_plan.offer_price = current_subscription.snapshot.price
    current_subscription.plan_id = "another-plan"

    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current_subscription

    await initiate_checkout_service.execute(checkout_command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved_subscription = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] == current_subscription.current_period_end
    assert saved_subscription.operation_type == SubscriptionOperationType.RENEWAL
    assert saved_subscription.current_period_start == current_subscription.current_period_end


@pytest.mark.asyncio
async def test_execute_does_not_save_subscription_if_gateway_fails(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    checkout_command,
):
    plan_repo.get_by_code.return_value = active_plan
    payment_gateway.create_checkout_session.side_effect = RuntimeError(
        "Payment gateway unavailable"
    )

    with pytest.raises(RuntimeError, match="Payment gateway unavailable"):
        await initiate_checkout_service.execute(checkout_command)

    subscription_repo.save.assert_not_awaited()
