"""Unit tests for Cashfree subscription adapter."""

import base64
import hashlib
import hmac
from decimal import Decimal

import pytest

from app.adapters.services.payment_gateway.cashfree import CashfreeSubscriptionAdapter
from app.core.config import Settings
from app.domain.entities.plan import BillingPeriod, Plan


@pytest.fixture
def test_plan() -> Plan:
    return Plan(
        code="lite_monthly",
        name="Lite",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("499.00"),
        offer_price=Decimal("299.00"),
        max_seconds_per_request=30,
        max_usage_per_day=50,
    )


def test_verify_webhook_signature_valid() -> None:
    secret = "secret-key-123"
    settings = Settings(cashfree_webhook_secret=secret, cashfree_secret_key=secret)
    adapter = CashfreeSubscriptionAdapter(settings)

    payload = b'{"event":"SUBSCRIPTION_ACTIVATION","data":{"subscription_id":"sub_1"}}'
    timestamp = "1728000000"

    message = timestamp.encode("utf-8") + payload
    valid_sig = base64.b64encode(
        hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    ).decode("utf-8")

    assert adapter.verify_webhook_signature(payload, valid_sig, timestamp) is True


def test_verify_webhook_signature_tampered_or_invalid() -> None:
    settings = Settings(cashfree_webhook_secret="", cashfree_secret_key="secret-key-123")
    adapter = CashfreeSubscriptionAdapter(settings)

    payload = b'{"event":"SUBSCRIPTION_ACTIVATION"}'
    assert adapter.verify_webhook_signature(payload, "bad_signature", "1728000000") is False
    assert adapter.verify_webhook_signature(payload, "", "1728000000") is False
    assert adapter.verify_webhook_signature(payload, "sig", "") is False


@pytest.mark.asyncio
async def test_create_checkout_session_mock_fallback(test_plan: Plan) -> None:
    settings = Settings(cashfree_app_id="", cashfree_secret_key="")
    adapter = CashfreeSubscriptionAdapter(settings)

    sub_id, checkout_session_id = await adapter.create_checkout_session(
        user_id="user-1",
        user_email="user1@example.com",
        plan=test_plan,
        return_url="https://return.url",
    )

    assert sub_id.startswith("sub_")
    assert checkout_session_id == f"session_mock_{sub_id}"


def test_cashfree_plan_interval_type_enum() -> None:
    from app.adapters.services.payment_gateway.cashfree import CashfreePlanIntervalType

    assert CashfreePlanIntervalType.DAY.value == "DAY"
    assert CashfreePlanIntervalType.WEEK.value == "WEEK"
    assert CashfreePlanIntervalType.MONTH.value == "MONTH"
    assert CashfreePlanIntervalType.YEAR.value == "YEAR"


@pytest.mark.asyncio
async def test_create_plan_sends_cashfree_plan_payload(test_plan: Plan) -> None:
    import json

    import httpx

    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(status_code=200, json={"plan_id": "lite_monthly"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    settings = Settings(
        cashfree_app_id="cf_real_app_id",
        cashfree_secret_key="cf_real_secret_key",
    )
    adapter = CashfreeSubscriptionAdapter(settings, client=mock_client)

    assert await adapter.create_plan(test_plan) is True

    request = captured_requests[-1]
    assert request.method == "POST"
    assert str(request.url) == "https://sandbox.cashfree.com/pg/plans"
    body = json.loads(request.content.decode("utf-8"))
    assert body["plan_id"] == "lite_monthly"
    assert body["plan_name"] == "Lite"
    assert body["plan_type"] == "PERIODIC"
    assert body["plan_currency"] == "INR"
    assert body["plan_recurring_amount"] == 299.0
    assert body["plan_max_amount"] == 299.0
    assert body["plan_intervals"] == 1
    assert body["plan_interval_type"] == "MONTH"


@pytest.mark.asyncio
async def test_delete_plan_calls_cashfree_plan_endpoint() -> None:
    import httpx

    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(status_code=200, json={"plan_id": "lite_monthly"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    settings = Settings(
        cashfree_app_id="cf_real_app_id",
        cashfree_secret_key="cf_real_secret_key",
    )
    adapter = CashfreeSubscriptionAdapter(settings, client=mock_client)

    assert await adapter.delete_plan("lite_monthly") is True

    request = captured_requests[-1]
    assert request.method == "DELETE"
    assert str(request.url) == "https://sandbox.cashfree.com/pg/plans/lite_monthly"


@pytest.mark.asyncio
async def test_create_checkout_session_sends_exact_cashfree_plan_interval_type() -> None:
    import json

    import httpx

    from app.adapters.services.payment_gateway.cashfree import CashfreePlanIntervalType

    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            status_code=200,
            json={
                "subscription_id": "sub_123",
                "subscription_session_id": "session_123",
            },
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    settings = Settings(
        cashfree_app_id="cf_real_app_id",
        cashfree_secret_key="cf_real_secret_key",
    )
    adapter = CashfreeSubscriptionAdapter(settings, client=mock_client)

    test_cases = [
        (BillingPeriod.MONTHLY, CashfreePlanIntervalType.MONTH.value),
        (BillingPeriod.WEEKLY, CashfreePlanIntervalType.WEEK.value),
        (BillingPeriod.DAILY, CashfreePlanIntervalType.DAY.value),
        (BillingPeriod.YEARLY, CashfreePlanIntervalType.YEAR.value),
    ]

    for period, expected_interval_type in test_cases:
        plan = Plan(
            code=f"test_{period.value}",
            name=f"Test {period.value}",
            billing_period=period,
            actual_price=Decimal("499.00"),
            offer_price=Decimal("299.00"),
            max_seconds_per_request=30,
            max_usage_per_day=50,
        )

        sub_id, checkout_session_id = await adapter.create_checkout_session(
            user_id="user-interval-test",
            user_email="test@effortless.app",
            plan=plan,
            return_url="https://return.url",
        )
        assert sub_id.startswith("sub_")
        assert checkout_session_id == "session_123"

        last_req = captured_requests[-1]
        body = json.loads(last_req.content.decode("utf-8"))
        assert body["plan_details"]["plan_interval_type"] == expected_interval_type
        assert expected_interval_type in ("DAY", "WEEK", "MONTH", "YEAR")


@pytest.mark.asyncio
async def test_create_checkout_session_sends_first_charge_time() -> None:
    import json
    from datetime import UTC, datetime

    import httpx

    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            status_code=200,
            json={
                "subscription_id": "sub_scheduled",
                "subscription_session_id": "session_scheduled",
            },
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    settings = Settings(
        cashfree_app_id="cf_real_app_id",
        cashfree_secret_key="cf_real_secret_key",
    )
    adapter = CashfreeSubscriptionAdapter(settings, client=mock_client)
    plan = Plan(
        code="test_scheduled",
        name="Test Scheduled",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("499.00"),
        offer_price=Decimal("299.00"),
        max_seconds_per_request=30,
        max_usage_per_day=50,
    )
    future_time = datetime(2026, 12, 1, 10, 0, 0, tzinfo=UTC)
    await adapter.create_checkout_session(
        user_id="user-future",
        user_email="future@effortless.app",
        plan=plan,
        return_url="https://return.url",
        first_charge_time=future_time,
    )

    last_req = captured_requests[-1]
    body = json.loads(last_req.content.decode("utf-8"))
    assert body["subscription_first_charge_time"] == "2026-12-01T10:00:00Z"
