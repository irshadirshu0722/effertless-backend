"""API integration tests for subscription endpoints."""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import (
    get_current_user,
    get_handle_webhook_use_case,
    get_initiate_checkout_use_case,
    get_list_plans_use_case,
    get_subscription_repo,
    get_user_subscription_use_case,
)
from app.application.use_case.initiate_checkout import (
    CheckoutSessionResult,
)
from app.core.exceptions import InvalidWebhookSignatureError
from app.domain.entities.authenticated_user import AuthenticatedUser
from app.domain.entities.plan import BillingPeriod, Plan
from app.domain.entities.subscription import Subscription
from main import app


class FakeListPlansUseCase:
    async def execute(self) -> list[Plan]:
        return [
            Plan(
                code="lite_monthly",
                name="Lite",
                billing_period=BillingPeriod.MONTHLY,
                actual_price=Decimal("499.00"),
                offer_price=Decimal("299.00"),
                max_seconds_per_request=30,
                max_usage_per_day=50,
            )
        ]


class FakeCheckoutUseCase:
    async def execute(self, user, plan_code, return_url):
        return CheckoutSessionResult(
            subscription_id="sub_test_123",
            checkout_session_id="session_test_123",
            status="pending",
        )


class FakeWebhookUseCase:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    async def execute(self, raw_payload, signature, timestamp, event_data):
        if self.should_fail:
            raise InvalidWebhookSignatureError()
        return True


class FakeSubscriptionRepo:
    async def get_active_by_user_id(self, user_id: str):
        return None

    async def save(self, subscription: Subscription):
        return subscription


class FakeUserSubscriptionUseCase:
    async def execute(self, user_id: str):
        from app.application.use_case.get_user_subscription import UserSubscriptionDetails
        from app.domain.value_objects.plan_snapshot import TierLimits
        from app.domain.value_objects.usage_balance import UsageBalance

        return UserSubscriptionDetails(
            status="active",
            plan_name="Pro",
            current_period_end=None,
            limits=TierLimits(max_seconds_per_request=120, max_usage_per_day=150),
            usage_today=UsageBalance(used_today=10, limit=150),
        )


@pytest.mark.asyncio
async def test_get_plans_public() -> None:
    app.dependency_overrides[get_list_plans_use_case] = lambda: FakeListPlansUseCase()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/subscriptions/plans")

    assert response.status_code == 200
    data = response.json()
    assert "plans" in data
    assert len(data["plans"]) == 1
    assert data["plans"][0]["code"] == "lite_monthly"
    assert data["plans"][0]["max_seconds_per_request"] == 30


@pytest.mark.asyncio
async def test_get_my_subscription_requires_auth() -> None:
    app.dependency_overrides[get_user_subscription_use_case] = lambda: FakeUserSubscriptionUseCase()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/subscriptions/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_get_my_subscription_authenticated() -> None:
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="user-pro")
    app.dependency_overrides[get_user_subscription_use_case] = lambda: FakeUserSubscriptionUseCase()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/subscriptions/me",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "limits" in data
    assert "usage_today" in data


@pytest.mark.asyncio
async def test_create_checkout_authenticated() -> None:
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="user-pro")
    app.dependency_overrides[get_initiate_checkout_use_case] = lambda: FakeCheckoutUseCase()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/subscriptions/checkout",
            headers={"Authorization": "Bearer valid-token"},
            json={
                "plan_code": "lite_monthly",
                "return_url": "https://effortless.app/success",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["subscription_id"] == "sub_test_123"
    assert data["checkout_session_id"] == "session_test_123"
    assert "payment_link" not in data


@pytest.mark.asyncio
async def test_webhook_invalid_signature() -> None:
    app.dependency_overrides[get_handle_webhook_use_case] = lambda: FakeWebhookUseCase(
        should_fail=True
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/subscriptions/webhook",
            headers={"x-webhook-signature": "bad_sig"},
            json={"event": "SUBSCRIPTION_ACTIVATION"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"


@pytest.mark.asyncio
async def test_webhook_valid_signature() -> None:
    app.dependency_overrides[get_handle_webhook_use_case] = lambda: FakeWebhookUseCase(
        should_fail=False
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/subscriptions/webhook",
            headers={"x-webhook-signature": "good_sig", "x-webhook-timestamp": "12345"},
            json={"event": "SUBSCRIPTION_ACTIVATION"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "acknowledged"}


@pytest.mark.asyncio
async def test_cancel_subscription_endpoint() -> None:
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="user-cancel")
    app.dependency_overrides[get_subscription_repo] = lambda: FakeSubscriptionRepo()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/subscriptions/cancel",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
