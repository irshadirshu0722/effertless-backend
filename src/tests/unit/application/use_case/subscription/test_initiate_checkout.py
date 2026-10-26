from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.use_case.plan.exceptions import PlanNotFoundError
from app.application.use_case.subscription.command import InitiateCheckoutCommand
from app.application.use_case.subscription.exceptions import (
    AlreadyHaveActiveSubscriptionError,
    TrailPlanNotFoundError,
)
from app.core.config import settings
from app.domain.entities.plan import PlanCode
from app.domain.entities.subscription import (
    ReplacementStrategy,
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
        actual_price=Decimal("0.00"),
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


def make_current_subscription(
    plan,
    *,
    status=SubscriptionStatus.ACTIVE,
    is_active=True,
    cancelled_at=None,
    period_end=None,
):
    now = datetime.now(UTC)

    return make_subscription_data(
        id=uuid4(),
        user_id="user-123",
        plan_id=plan.id,
        status=status,
        is_active=is_active,
        cancelled_at=cancelled_at,
        current_period_start=now - timedelta(days=5),
        current_period_end=period_end or now + timedelta(days=25),
        snapshot_plan_name=plan.name,
        snapshot_max_seconds=plan.monthly_seconds,
        snapshot_price=plan.offer_price,
        snapshot_currency=plan.currency,
        has_trial=False,
    )


def assert_saved_snapshot(saved, plan):
    assert saved.snapshot_plan_name == plan.name
    assert saved.snapshot_max_seconds == plan.monthly_seconds
    assert saved.snapshot_currency == plan.currency
    assert saved.snapshot_price == plan.offer_price


# ---------------------------------------------------------
# New subscription and trial
# ---------------------------------------------------------


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

    plan_repo.get_by_code.side_effect = [active_plan, trail_plan]
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
    assert saved.trial_end - saved.trial_start == timedelta(days=7)
    assert saved.current_period_start == saved.trial_end
    assert saved.replacement_strategy is None

    assert_saved_snapshot(saved, active_plan)


@pytest.mark.asyncio
async def test_execute_creates_new_subscription_without_trial_if_already_used(
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
    assert saved.operation_type == SubscriptionOperationType.NEW
    assert saved.replacement_strategy is None

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
        if str(code).upper() == "PRO":
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
@pytest.mark.parametrize(
    "changes",
    [
        {"is_active": False},
        {"is_deleted": True},
    ],
)
async def test_execute_rejects_unavailable_trial_plan(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    trail_plan,
    checkout_command,
    changes,
):
    async def get_by_code(code):
        if str(code).upper() == "PRO":
            return active_plan
        if str(code).upper() == "TRAIL":
            return replace(trail_plan, **changes)
        return None

    plan_repo.get_by_code.side_effect = get_by_code
    subscription_repo.get_active_by_user_id.return_value = None
    subscription_repo.has_user_used_trial.return_value = False

    with pytest.raises(TrailPlanNotFoundError):
        await initiate_checkout_service.execute(checkout_command)

    payment_gateway.create_checkout_session.assert_not_awaited()
    subscription_repo.save.assert_not_awaited()


# ---------------------------------------------------------
# Plan validation
# ---------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
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
    changes,
):
    plan_repo.get_by_code.return_value = replace(active_plan, **changes)

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


# ---------------------------------------------------------
# Operation type mapping
# ---------------------------------------------------------


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

    result = initiate_checkout_service._find_operation_type(
        current_code,
        plan,
    )

    assert result == expected


# ---------------------------------------------------------
# Active subscription: immediate replacement
# ---------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_code", "new_code", "expected_operation"),
    [
        ("BASIC", "STANDARD", SubscriptionOperationType.UPGRADE),
        ("BASIC", "PRO", SubscriptionOperationType.UPGRADE),
        ("STANDARD", "PRO", SubscriptionOperationType.UPGRADE),
        ("PRO", "STANDARD", SubscriptionOperationType.DOWNGRADE),
        ("PRO", "BASIC", SubscriptionOperationType.DOWNGRADE),
        ("STANDARD", "BASIC", SubscriptionOperationType.DOWNGRADE),
        ("PRO", "PRO", SubscriptionOperationType.RENEWAL),
    ],
)
async def test_execute_immediate_replacement(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    user,
    current_code,
    new_code,
    expected_operation,
):
    current_plan = make_plan(
        code=current_code,
        name=current_code.title(),
        price={
            "BASIC": "10.00",
            "STANDARD": "20.00",
            "PRO": "30.00",
        }[current_code],
        plan_id=f"current-{current_code.lower()}",
    )
    new_plan = make_plan(
        code=new_code,
        name=new_code.title(),
        price={
            "BASIC": "10.00",
            "STANDARD": "20.00",
            "PRO": "30.00",
        }[new_code],
        plan_id=f"new-{new_code.lower()}",
    )

    current = make_current_subscription(current_plan)

    command = InitiateCheckoutCommand(
        user=user,
        plan_code=new_code,
        return_url="https://example.com/checkout/return",
        replace=True,
    )

    plan_repo.get_by_code.return_value = new_plan
    subscription_repo.get_active_by_user_id.return_value = current

    await initiate_checkout_service.execute(command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] is None
    assert saved.operation_type == expected_operation
    assert saved.related_subscription_id == current.id
    assert saved.replacement_strategy == ReplacementStrategy.IMMEDIATE
    assert saved.has_trial is False
    assert_saved_snapshot(saved, new_plan)

    subscription_repo.has_user_used_trial.assert_not_awaited()


# ---------------------------------------------------------
# Active subscription: replacement at period end
# ---------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_code", "new_code", "expected_operation"),
    [
        ("BASIC", "STANDARD", SubscriptionOperationType.UPGRADE),
        ("BASIC", "PRO", SubscriptionOperationType.UPGRADE),
        ("STANDARD", "PRO", SubscriptionOperationType.UPGRADE),
        ("PRO", "STANDARD", SubscriptionOperationType.DOWNGRADE),
        ("PRO", "BASIC", SubscriptionOperationType.DOWNGRADE),
        ("STANDARD", "BASIC", SubscriptionOperationType.DOWNGRADE),
    ],
)
async def test_execute_schedules_plan_change_at_period_end(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    user,
    current_code,
    new_code,
    expected_operation,
):
    current_plan = make_plan(
        code=current_code,
        name=current_code.title(),
        price={
            "BASIC": "10.00",
            "STANDARD": "20.00",
            "PRO": "30.00",
        }[current_code],
        plan_id=f"current-{current_code.lower()}",
    )
    new_plan = make_plan(
        code=new_code,
        name=new_code.title(),
        price={
            "BASIC": "10.00",
            "STANDARD": "20.00",
            "PRO": "30.00",
        }[new_code],
        plan_id=f"new-{new_code.lower()}",
    )

    current = make_current_subscription(current_plan)

    command = InitiateCheckoutCommand(
        user=user,
        plan_code=new_code,
        return_url="https://example.com/checkout/return",
        replace=False,
    )

    plan_repo.get_by_code.return_value = new_plan
    subscription_repo.get_active_by_user_id.return_value = current

    await initiate_checkout_service.execute(command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] == current.current_period_end
    assert saved.current_period_start == current.current_period_end
    assert saved.operation_type == expected_operation
    assert saved.related_subscription_id == current.id
    assert saved.replacement_strategy == ReplacementStrategy.PERIOD_END
    assert saved.has_trial is False


# ---------------------------------------------------------
# Duplicate active same-plan purchase
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_rejects_active_same_plan_when_replace_is_false(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    user,
):
    current = make_current_subscription(active_plan)

    command = InitiateCheckoutCommand(
        user=user,
        plan_code=str(active_plan.code),
        return_url="https://example.com/checkout/return",
        replace=False,
    )

    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current

    with pytest.raises(AlreadyHaveActiveSubscriptionError):
        await initiate_checkout_service.execute(command)

    payment_gateway.create_checkout_session.assert_not_awaited()
    subscription_repo.save.assert_not_awaited()


# ---------------------------------------------------------
# Cancelled/inactive subscription renewal
# ---------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("replace_now", "expected_strategy"),
    [
        (True, ReplacementStrategy.IMMEDIATE),
        (False, ReplacementStrategy.PERIOD_END),
    ],
)
async def test_execute_renews_inactive_same_plan(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    user,
    replace_now,
    expected_strategy,
):
    period_end = datetime.now(UTC) + timedelta(days=10)

    current = make_current_subscription(
        active_plan,
        status=SubscriptionStatus.CANCELLED,
        is_active=False,
        cancelled_at=datetime.now(UTC),
        period_end=period_end,
    )

    command = InitiateCheckoutCommand(
        user=user,
        plan_code=str(active_plan.code),
        return_url="https://example.com/checkout/return",
        replace=replace_now,
    )

    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current

    await initiate_checkout_service.execute(command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved = subscription_repo.save.await_args.args[0]

    if replace_now:
        assert gateway_kwargs["first_charge_time"] is None
    else:
        assert gateway_kwargs["first_charge_time"] == period_end

    assert saved.operation_type == SubscriptionOperationType.RENEWAL
    assert saved.replacement_strategy == expected_strategy
    assert saved.related_subscription_id == current.id


# ---------------------------------------------------------
# Expired subscription period
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_does_not_schedule_at_a_past_period_end(
    initiate_checkout_service,
    plan_repo,
    subscription_repo,
    payment_gateway,
    active_plan,
    user,
):
    now = datetime.now(UTC)

    current = make_current_subscription(
        make_plan(
            code="BASIC",
            name="Basic",
            price="10.00",
            plan_id="old-basic",
        ),
        period_end=now - timedelta(days=1),
    )

    command = InitiateCheckoutCommand(
        user=user,
        plan_code="PRO",
        return_url="https://example.com/checkout/return",
        replace=False,
    )

    plan_repo.get_by_code.return_value = active_plan
    subscription_repo.get_active_by_user_id.return_value = current

    await initiate_checkout_service.execute(command)

    gateway_kwargs = payment_gateway.create_checkout_session.await_args.kwargs
    saved = subscription_repo.save.await_args.args[0]

    assert gateway_kwargs["first_charge_time"] is None
    assert saved.operation_type == SubscriptionOperationType.NEW
    assert saved.replacement_strategy is None


# ---------------------------------------------------------
# Gateway and persistence failures
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_does_not_save_if_gateway_fails(
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


@pytest.mark.asyncio
async def test_execute_propagates_subscription_save_failure(
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

    subscription_repo.save.side_effect = RuntimeError("Database unavailable")

    with pytest.raises(RuntimeError, match="Database unavailable"):
        await initiate_checkout_service.execute(checkout_command)

    payment_gateway.create_checkout_session.assert_awaited_once()
    subscription_repo.save.assert_awaited_once()
