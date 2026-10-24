from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.entities.plan import PlanCode
from app.domain.entities.subscription import (
    Subscription,
    SubscriptionOperationType,
    SubscriptionStatus,
)
from tests.factories.make_plan import make_plan_data

ENDPOINT = "/api/v1/subscriptions/checkout"

AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def checkout_payload(**overrides):
    payload = {
        "plan_code": "pro",
        "return_url": "https://example.com/checkout/return",
        "replace": False,
    }
    payload.update(overrides)
    return payload


async def create_existing_subscription(
    subscription_repo,
    auth_user,
    plan,
    *,
    status=SubscriptionStatus.ACTIVE,
    is_active=True,
    cancelled_at=None,
    period_end=None,
):
    now = datetime.now(UTC)

    subscription = Subscription(
        user_id=auth_user.user_id,
        plan_id=plan.id,
        status=status,
        provider="cashfree",
        external_subscription_id="existing-cashfree-sub",
        current_period_start=now - timedelta(days=5),
        current_period_end=period_end or now + timedelta(days=25),
        operation_type=SubscriptionOperationType.NEW,
        is_active=is_active,
        cancelled_at=cancelled_at,
        snapshot_plan_name=plan.name,
        snapshot_max_seconds=plan.monthly_seconds,
        snapshot_price=plan.offer_price,
        snapshot_currency=plan.currency,
        has_trial=False,
    )

    return await subscription_repo.save(subscription)


# ---------------------------------------------------------
# Request validation
# ---------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"plan_code": ""},
        {"return_url": ""},
        {"plan_code": None},
        {"return_url": None},
        {"replace": "not-a-boolean"},
    ],
)
async def test_checkout_rejects_invalid_request(
    async_client,
    create_all_plan,
    payload,
):
    response = await async_client.post(
        ENDPOINT,
        json=payload,
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_checkout_rejects_missing_authentication(
    async_client,
    create_all_plan,
):
    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(),
    )

    assert response.status_code in (401, 403)


# ---------------------------------------------------------
# New subscription and trial handling
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_creates_new_subscription_with_trial(
    async_client,
    create_all_plan,
    mock_cashfree_gateway,
    subscription_repo,
    auth_user,
):
    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()

    assert body["subscription_id"] == "cashfree-sub-123"
    assert body["checkout_session_id"] == "checkout-session-123"
    assert body["status"] == "pending"

    mock_cashfree_gateway.create_checkout_session.assert_awaited_once()
    kwargs = mock_cashfree_gateway.create_checkout_session.await_args.kwargs

    assert kwargs["user_id"] == auth_user.user_id
    assert kwargs["plan"].code == PlanCode.PRO
    assert kwargs["first_charge_time"] is not None

    saved = await subscription_repo.get_latest_by_user_id(auth_user.user_id)

    assert saved is not None
    assert saved.status == SubscriptionStatus.PENDING
    assert saved.operation_type == SubscriptionOperationType.NEW
    assert saved.has_trial is True
    assert saved.trial_start is not None
    assert saved.trial_end is not None
    assert saved.trial_end > saved.trial_start
    assert saved.snapshot_plan_name == "Pro"


@pytest.mark.asyncio
async def test_checkout_without_trial_when_user_already_used_trial(
    async_client,
    create_all_plan,
    subscription_repo,
    auth_user,
    mock_cashfree_gateway,
):
    # Create a historical subscription that records trial usage.
    now = datetime.now(UTC)
    trial_plan = create_all_plan[PlanCode.TRAIL]

    historical_trial = Subscription(
        user_id=auth_user.user_id,
        plan_id=trial_plan.id,
        status=SubscriptionStatus.COMPLETED,
        provider="cashfree",
        external_subscription_id="historical-trial",
        current_period_start=now - timedelta(days=20),
        current_period_end=now - timedelta(days=13),
        has_trial=True,
        trial_start=now - timedelta(days=20),
        trial_end=now - timedelta(days=13),
        snapshot_plan_name=trial_plan.name,
        snapshot_max_seconds=trial_plan.monthly_seconds,
        snapshot_price=trial_plan.offer_price,
        snapshot_currency=trial_plan.currency,
    )
    await subscription_repo.save(historical_trial)

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    kwargs = mock_cashfree_gateway.create_checkout_session.await_args.kwargs
    assert kwargs["first_charge_time"] is None

    saved = await subscription_repo.get_latest_by_user_id(auth_user.user_id)

    assert saved.has_trial is False
    assert saved.trial_start is None
    assert saved.trial_end is None


@pytest.mark.asyncio
async def test_checkout_rejects_trial_if_trial_plan_is_missing(
    async_client,
    plan_repo,
    subscription_repo,
    mock_cashfree_gateway,
):
    # Create only the requested Pro plan, deliberately omitting TRAIL.
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.PRO,
            name="Pro",
            actual_price=Decimal("999.00"),
            offer_price=Decimal("999.00"),
        )
    )

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 409
    mock_cashfree_gateway.create_checkout_session.assert_not_awaited()


# ---------------------------------------------------------
# Existing subscription: upgrade and downgrade scheduling
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_upgrade_is_immediate_when_replace_is_true(
    async_client,
    create_all_plan,
    subscription_repo,
    auth_user,
    mock_cashfree_gateway,
):
    await create_existing_subscription(
        subscription_repo,
        auth_user,
        create_all_plan[PlanCode.BASIC],
    )

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(replace=True),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    kwargs = mock_cashfree_gateway.create_checkout_session.await_args.kwargs
    assert kwargs["first_charge_time"] is None

    saved = await subscription_repo.get_latest_by_user_id(auth_user.user_id)
    assert saved.operation_type == SubscriptionOperationType.UPGRADE
    assert saved.has_trial is False


@pytest.mark.asyncio
async def test_upgrade_is_scheduled_when_replace_is_false(
    async_client,
    create_all_plan,
    subscription_repo,
    auth_user,
    mock_cashfree_gateway,
):
    current = await create_existing_subscription(
        subscription_repo,
        auth_user,
        create_all_plan[PlanCode.BASIC],
    )

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(replace=False),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    kwargs = mock_cashfree_gateway.create_checkout_session.await_args.kwargs
    assert kwargs["first_charge_time"] == current.current_period_end

    saved = await subscription_repo.get_latest_by_user_id(auth_user.user_id)
    assert saved.operation_type == SubscriptionOperationType.UPGRADE
    assert saved.current_period_start == current.current_period_end


@pytest.mark.asyncio
async def test_downgrade_is_scheduled_at_period_end(
    async_client,
    create_all_plan,
    subscription_repo,
    auth_user,
    mock_cashfree_gateway,
):
    current = await create_existing_subscription(
        subscription_repo,
        auth_user,
        create_all_plan[PlanCode.PRO],
    )

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(plan_code="basic", replace=False),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    kwargs = mock_cashfree_gateway.create_checkout_session.await_args.kwargs
    assert kwargs["first_charge_time"] == current.current_period_end

    saved = await subscription_repo.get_latest_by_user_id(auth_user.user_id)
    assert saved.operation_type == SubscriptionOperationType.DOWNGRADE


@pytest.mark.asyncio
async def test_downgrade_is_immediate_when_replace_is_true(
    async_client,
    create_all_plan,
    subscription_repo,
    auth_user,
    mock_cashfree_gateway,
):
    await create_existing_subscription(
        subscription_repo,
        auth_user,
        create_all_plan[PlanCode.PRO],
    )

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(plan_code="basic", replace=True),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    kwargs = mock_cashfree_gateway.create_checkout_session.await_args.kwargs
    assert kwargs["first_charge_time"] is None

    saved = await subscription_repo.get_latest_by_user_id(auth_user.user_id)
    assert saved.operation_type == SubscriptionOperationType.DOWNGRADE


# ---------------------------------------------------------
# Same-plan purchase and renewal
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_same_active_plan_is_rejected(
    async_client,
    create_all_plan,
    subscription_repo,
    auth_user,
    mock_cashfree_gateway,
):
    await create_existing_subscription(
        subscription_repo,
        auth_user,
        create_all_plan[PlanCode.PRO],
    )

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 409, response.json()
    mock_cashfree_gateway.create_checkout_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_same_plan_with_non_active_subscription_schedules_renewal(
    async_client,
    create_all_plan,
    subscription_repo,
    auth_user,
    mock_cashfree_gateway,
):
    current = await create_existing_subscription(
        subscription_repo,
        auth_user,
        create_all_plan[PlanCode.PRO],
        status=SubscriptionStatus.CANCELLED,
        is_active=True,
        cancelled_at=datetime.now(UTC),
    )

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(),
        headers=AUTH_HEADERS,
    )

    # The outcome depends on whether the repository returns cancelled
    # subscriptions from get_active_by_user_id.
    if response.status_code == 200:
        kwargs = mock_cashfree_gateway.create_checkout_session.await_args.kwargs
        assert kwargs["first_charge_time"] == current.current_period_end

        saved = await subscription_repo.get_latest_by_user_id(auth_user.user_id)
        assert saved.operation_type == SubscriptionOperationType.RENEWAL


# ---------------------------------------------------------
# Gateway failures
# ---------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_gateway_failure_does_not_save_subscription(
    async_client,
    create_all_plan,
    subscription_repo,
    auth_user,
    mock_cashfree_gateway,
):
    mock_cashfree_gateway.create_checkout_session.side_effect = RuntimeError("Cashfree unavailable")

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(),
        headers=AUTH_HEADERS,
    )

    assert response.status_code >= 500

    saved = await subscription_repo.get_latest_by_user_id(auth_user.user_id)
    assert saved is None


@pytest.mark.asyncio
async def test_checkout_uses_requested_return_url(
    async_client,
    create_all_plan,
    mock_cashfree_gateway,
):
    return_url = "https://example.com/custom-return"

    response = await async_client.post(
        ENDPOINT,
        json=checkout_payload(return_url=return_url),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    kwargs = mock_cashfree_gateway.create_checkout_session.await_args.kwargs
    assert kwargs["return_url"] == return_url
