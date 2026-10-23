from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.use_case.subscription import PlanNotFoundError
from app.application.use_case.subscription.command import InitiateCheckoutCommand
from app.application.use_case.subscription.exceptions import TrailPlanNotFoundError
from app.core.config import settings
from app.core.exceptions import ActiveSubscriptionError
from app.domain.entities.plan import PlanCode
from app.domain.entities.subscription import (
    SubscriptionOperationType,
    SubscriptionStatus,
)
from tests.factories import make_plan_data, make_subscription_data


@pytest.fixture
def checkout_command(user):
    return InitiateCheckoutCommand(
        user=user,
        plan_code="PRO",
        return_url="https://example.com/checkout/return",
        replace=True,
    )


@pytest.fixture
def current_subscription():
    now = datetime.now(UTC)
    return make_subscription_data(
        id=uuid4(),
        user_id="user-123",
        plan_id="plan-basic",
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
        cancelled_at=None,
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        snapshot_plan_name="Basic",
        snapshot_max_seconds=3600,
        snapshot_price=Decimal("10.00"),
        snapshot_currency="PLN",
    )


@pytest.fixture
def trail_plan():
    return make_plan_data(
        id=uuid4(),
        code=PlanCode.TRAIL,
        name="Trail",
        monthly_seconds=600,
        offer_price=Decimal("0.00"),
        currency="PLN",
        is_active=True,
        is_deleted=False,
    )


def make_plan(
    *,
    code,
    name,
    price,
    plan_id,
    monthly_seconds=3600,
):
    return make_plan_data(
        id=plan_id,
        code=PlanCode(code),
        name=name,
        monthly_seconds=monthly_seconds,
        actual_price=Decimal(price),
        offer_price=Decimal(price),
        currency="PLN",
        is_active=True,
        is_deleted=False,
    )


@pytest.mark.asyncio
async def test_execute_creates_new_pending_subscription_with_trial(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    trail_plan,
    checkout_command,
    monkeypatch,
):
    monkeypatch.setattr(settings, "free_tier_days", 7)
    plan_repo.get_by_code.side_effect = [
        active_plan,
        trail_plan,
    ]
    subscription_repo.get_active_by_user_id.return_value = None
    subscription_repo.has_user_used_trial.return_value = False

    before = datetime.now(UTC)
    result = await initiate_checkout_service.execute(checkout_command)
    after = datetime.now(UTC)

    assert result.subscription_id == "cashfree-sub-123"
    assert result.checkout_session_id == "checkout-session-123"
    assert result.status == "pending"

    subscription_repo.get_active_by_user_id.assert_awaited_once_with("user-123")
    subscription_repo.has_user_used_trial.assert_awaited_once_with(user_id="user-123")

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    assert gateway_kwargs["user_id"] == "user-123"
    assert gateway_kwargs["user_email"] == "user@example.com"
    assert gateway_kwargs["plan"] == active_plan
    assert gateway_kwargs["return_url"] == ("https://example.com/checkout/return")
    assert before + timedelta(days=7) <= gateway_kwargs["first_charge_time"]
    assert gateway_kwargs["first_charge_time"] <= after + timedelta(days=7)

    subscription_repo.save.assert_awaited_once()
    saved = subscription_repo.save.await_args.args[0]

    assert saved.user_id == "user-123"
    assert saved.plan_id == active_plan.id
    assert saved.status == SubscriptionStatus.PENDING
    assert saved.provider == "cashfree"
    assert saved.external_subscription_id == "cashfree-sub-123"
    assert saved.operation_type == SubscriptionOperationType.NEW
    assert saved.related_subscription_id is None

    assert saved.has_trial is True
    assert saved.trial_start is not None
    assert saved.trial_end is not None
    assert saved.trial_end - saved.trial_start == timedelta(days=7)
    assert saved.current_period_start == saved.trial_end

    assert saved.snapshot_plan_name == active_plan.name
    assert saved.snapshot_price == active_plan.offer_price
    assert saved.snapshot_currency == active_plan.currency
    assert saved.snapshot_max_seconds == active_plan.monthly_seconds


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
    plan_repo.get_by_code.return_value = replace(active_plan, **plan_changes)

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
    current = make_subscription_data(
        id=uuid4(),
        user_id="user-123",
        plan_id=active_plan.id,
        status=SubscriptionStatus.ACTIVE,
        is_active=True,
        cancelled_at=None,
        current_period_start=datetime.now(UTC) - timedelta(days=20),
        current_period_end=datetime.now(UTC) + timedelta(days=10),
        snapshot_plan_name="Pro",
        snapshot_max_seconds=active_plan.monthly_seconds,
        snapshot_price=active_plan.offer_price,
        snapshot_currency=active_plan.currency,
    )

    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current

    with pytest.raises(ActiveSubscriptionError):
        await initiate_checkout_service.execute(checkout_command)

    payment_gateway.create_checkout_session.assert_not_awaited()
    subscription_repo.save.assert_not_awaited()
    subscription_repo.has_user_used_trial.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_starts_upgrade_immediately_when_replace_is_true(
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

    await initiate_checkout_service.execute(checkout_command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] is None
    assert saved.operation_type == SubscriptionOperationType.UPGRADE
    assert saved.related_subscription_id == current_subscription.id
    assert saved.status == SubscriptionStatus.PENDING
    assert saved.has_trial is False

    subscription_repo.has_user_used_trial.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_schedules_upgrade_at_period_end_when_replace_is_false(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    user,
    current_subscription,
):
    command = InitiateCheckoutCommand(
        user=user,
        plan_code="pro",
        return_url="https://example.com/checkout/return",
        replace=False,
    )
    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current_subscription

    await initiate_checkout_service.execute(command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] == (current_subscription.current_period_end)
    assert saved.operation_type == SubscriptionOperationType.UPGRADE
    assert saved.current_period_start == current_subscription.current_period_end


@pytest.mark.asyncio
async def test_execute_schedules_downgrade_at_period_end(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    user,
    current_subscription,
):
    basic_plan = make_plan(
        code="BASIC",
        name="Basic",
        price="5.00",
        plan_id="plan-basic-new",
    )
    command = InitiateCheckoutCommand(
        user=user,
        plan_code="basic",
        return_url="https://example.com/checkout/return",
        replace=False,
    )
    current_subscription.snapshot_plan_name = "PRO"
    plan_repo.get_by_code.return_value = basic_plan
    subscription_repo.get_active_by_user_id.return_value = current_subscription

    await initiate_checkout_service.execute(command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] == (current_subscription.current_period_end)
    assert saved.operation_type == SubscriptionOperationType.DOWNGRADE
    assert saved.current_period_start == current_subscription.current_period_end
    assert saved.related_subscription_id == current_subscription.id


@pytest.mark.asyncio
async def test_execute_does_not_apply_trial_if_user_already_used_trial(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    checkout_command,
):
    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = None
    subscription_repo.has_user_used_trial.return_value = True

    await initiate_checkout_service.execute(checkout_command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] is None
    assert saved.has_trial is False
    assert saved.trial_start is None
    assert saved.trial_end is None
    plan_repo.get_by_code.assert_awaited_once_with("PRO")


@pytest.mark.asyncio
async def test_execute_raises_if_trial_plan_is_missing(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    checkout_command,
):
    async def get_by_code(code):
        if str(code).lower() == "pro":
            return active_plan
        return None

    plan_repo.get_by_code.side_effect = get_by_code
    subscription_repo.get_active_by_user_id.return_value = None
    subscription_repo.has_user_used_trial.return_value = False

    with pytest.raises(TrailPlanNotFoundError):
        await initiate_checkout_service.execute(checkout_command)

    payment_gateway.create_checkout_session.assert_not_awaited()
    subscription_repo.save.assert_not_awaited()


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
    subscription_repo.get_active_by_user_id.return_value = None
    subscription_repo.has_user_used_trial.return_value = True
    payment_gateway.create_checkout_session.side_effect = RuntimeError(
        "Payment gateway unavailable"
    )

    with pytest.raises(RuntimeError, match="Payment gateway unavailable"):
        await initiate_checkout_service.execute(checkout_command)

    subscription_repo.save.assert_not_awaited()


@pytest.mark.parametrize(
    ("current_code", "new_code", "expected"),
    [
        ("BASIC", "STANDARD", SubscriptionOperationType.UPGRADE),
        ("BASIC", "PRO", SubscriptionOperationType.UPGRADE),
        ("STANDARD", "PRO", SubscriptionOperationType.UPGRADE),
        ("PRO", "STANDARD", SubscriptionOperationType.DOWNGRADE),
        ("PRO", "BASIC", SubscriptionOperationType.DOWNGRADE),
        ("STANDARD", "BASIC", SubscriptionOperationType.DOWNGRADE),
        ("BASIC", "BASIC", SubscriptionOperationType.RENEWAL),
        ("STANDARD", "STANDARD", SubscriptionOperationType.RENEWAL),
        ("PRO", "PRO", SubscriptionOperationType.RENEWAL),
    ],
)
def test_find_operation_type(
    initiate_checkout_service,
    current_code,
    new_code,
    expected,
):
    plan = make_plan(
        code=new_code,
        name=new_code.title(),
        price="10.00",
        plan_id=f"plan-{new_code.lower()}",
    )

    result = initiate_checkout_service._find_operation_type(current_code, plan)

    assert result == expected


@pytest.mark.asyncio
async def test_execute_schedules_same_plan_renewal_when_subscription_is_not_active(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    user,
):
    period_end = datetime.now(UTC) + timedelta(days=10)
    current = make_subscription_data(
        id=uuid4(),
        user_id="user-123",
        plan_id=active_plan.id,
        status=SubscriptionStatus.CANCELLED,
        is_active=False,
        cancelled_at=datetime.now(UTC),
        current_period_start=period_end - timedelta(days=30),
        current_period_end=period_end,
        snapshot_plan_name="Pro",
        snapshot_max_seconds=active_plan.monthly_seconds,
        snapshot_price=active_plan.offer_price,
        snapshot_currency=active_plan.currency,
    )
    command = InitiateCheckoutCommand(
        user=user,
        plan_code="PRO",
        return_url="https://example.com/checkout/return",
        replace=True,
    )
    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current

    await initiate_checkout_service.execute(command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] == period_end
    assert saved.operation_type == SubscriptionOperationType.RENEWAL
    assert saved.current_period_start == period_end


@pytest.mark.asyncio
async def test_execute_does_not_apply_trial_when_existing_subscription_is_found(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    current_subscription,
    checkout_command,
):
    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current_subscription

    await initiate_checkout_service.execute(checkout_command)

    saved = subscription_repo.save.await_args.args[0]

    assert saved.has_trial is False
    assert saved.trial_start is None
    assert saved.trial_end is None
    subscription_repo.has_user_used_trial.assert_not_awaited()
