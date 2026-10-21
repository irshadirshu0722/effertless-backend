import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from app.adapters.services import (
    CashfreeSubscriptionAdapter,
)
from app.core.exceptions import SubscriptionPaymentError
from app.domain.entities.plan import BillingPeriod
from tests.factories import make_plan_data


@pytest.fixture
def settings():
    """Valid non-mock Cashfree configuration."""
    return SimpleNamespace(
        cashfree_environment="sandbox",
        cashfree_app_id="cf_test_app_id",
        cashfree_secret_key="test-secret-key",
        cashfree_webhook_secret="test-webhook-secret",
    )


@pytest.fixture
def plan():
    return make_plan_data()


@pytest.fixture
def adapter(settings):
    return CashfreeSubscriptionAdapter(settings)


def make_client(handler):
    """Create an HTTP client that never makes real network requests."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# Configuration and request helpers
# ---------------------------------------------------------------------------


def test_sandbox_base_url(settings):
    adapter = CashfreeSubscriptionAdapter(settings)

    assert adapter._base_url == "https://sandbox.cashfree.com/pg"


def test_production_base_url(settings):
    settings.cashfree_environment = "production"

    adapter = CashfreeSubscriptionAdapter(settings)

    assert adapter._base_url == "https://api.cashfree.com/pg"


def test_mock_mode_when_credentials_missing(settings):
    settings.cashfree_app_id = ""

    adapter = CashfreeSubscriptionAdapter(settings)

    assert adapter._is_mock_mode() is True


def test_mock_mode_for_test_app_id(settings):
    settings.cashfree_app_id = "test_my_app"

    adapter = CashfreeSubscriptionAdapter(settings)

    assert adapter._is_mock_mode() is True


def test_real_mode_with_configured_credentials(adapter):
    assert adapter._is_mock_mode() is False


def test_headers_include_required_authentication(adapter):
    headers = adapter._headers()

    assert headers["x-client-id"] == "cf_test_app_id"
    assert headers["x-client-secret"] == "test-secret-key"
    assert headers["x-api-version"] == "2025-01-01"
    assert "Content-Type" not in headers


def test_headers_include_content_type_when_requested(adapter):
    headers = adapter._headers(include_content_type=True)

    assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# Plan payload and billing interval mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("billing_period", "expected_interval"),
    [
        (BillingPeriod.DAILY, "DAY"),
        (BillingPeriod.WEEKLY, "WEEK"),
        (BillingPeriod.MONTHLY, "MONTH"),
        (BillingPeriod.YEARLY, "YEAR"),
    ],
)
def test_plan_payload_maps_billing_period(
    adapter,
    plan,
    billing_period,
    expected_interval,
):
    plan.billing_period = billing_period

    payload = adapter._plan_payload(plan)

    assert payload["plan_id"] == plan.code
    assert payload["plan_name"] == plan.name
    assert payload["plan_type"] == "PERIODIC"
    assert payload["plan_currency"] == plan.currency
    assert payload["plan_recurring_amount"] == float(plan.offer_price)
    assert payload["plan_max_amount"] == float(plan.offer_price)
    assert payload["plan_intervals"] == 1
    assert payload["plan_interval_type"] == expected_interval
    assert payload["plan_note"] == f"Effortless plan {plan.code}"


def test_first_charge_time_converts_to_utc():
    # UTC+02:00 should be converted to UTC.
    local_time = datetime(
        2026,
        10,
        21,
        12,
        30,
        tzinfo=timezone(timedelta(hours=2)),
    )

    result = CashfreeSubscriptionAdapter._first_charge_time_for_cashfree(local_time)

    assert result == "2026-10-21T10:30:00Z"


def test_first_charge_time_treats_naive_datetime_as_utc():
    naive_time = datetime(2026, 10, 21, 10, 30)

    result = CashfreeSubscriptionAdapter._first_charge_time_for_cashfree(naive_time)

    assert result == "2026-10-21T10:30:00Z"


# ---------------------------------------------------------------------------
# Create plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_plan_sends_expected_request(settings, plan):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == "https://sandbox.cashfree.com/pg/plans"
        assert request.headers["x-client-id"] == "cf_test_app_id"
        assert request.headers["Content-Type"] == "application/json"

        payload = json.loads(request.content)
        assert payload["plan_id"] == plan.code
        assert payload["plan_recurring_amount"] == float(plan.offer_price)

        return httpx.Response(200, json={"status": "OK"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        assert await gateway.create_plan(plan) is True


@pytest.mark.asyncio
async def test_create_plan_returns_true_in_mock_mode(settings, plan):
    settings.cashfree_app_id = "test_mock_app"

    async def fail_if_called(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Cashfree should not be called in mock mode")

    async with make_client(fail_if_called) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        assert await gateway.create_plan(plan) is True


@pytest.mark.asyncio
async def test_create_plan_raises_on_api_error(settings, plan):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "Invalid plan"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        with pytest.raises(SubscriptionPaymentError):
            await gateway.create_plan(plan)


@pytest.mark.asyncio
async def test_create_plan_raises_on_network_error(settings, plan):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        with pytest.raises(SubscriptionPaymentError, match="Network error"):
            await gateway.create_plan(plan)


# ---------------------------------------------------------------------------
# Delete plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_plan_sends_expected_request(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path.endswith("/plans/PLN")
        return httpx.Response(200, json={"status": "OK"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        assert await gateway.delete_plan("PLN") is True


@pytest.mark.asyncio
async def test_delete_plan_returns_true_when_plan_is_missing(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not found"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        assert await gateway.delete_plan("PLN") is True


@pytest.mark.asyncio
async def test_delete_plan_raises_on_api_error(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal server error")

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        with pytest.raises(SubscriptionPaymentError):
            await gateway.delete_plan("PLN")


@pytest.mark.asyncio
async def test_delete_plan_raises_on_network_error(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        with pytest.raises(SubscriptionPaymentError, match="Network error"):
            await gateway.delete_plan("PLN")


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------


def generate_signature(secret: str, timestamp: str, raw_payload: bytes) -> str:
    message = timestamp.encode("utf-8") + raw_payload
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def test_verify_webhook_signature_accepts_valid_signature(adapter):
    timestamp = "1720000000000"
    raw_payload = b'{"type":"SUBSCRIPTION_STATUS_CHANGED"}'
    signature = generate_signature(
        "test-webhook-secret",
        timestamp,
        raw_payload,
    )

    assert (
        adapter.verify_webhook_signature(
            raw_payload,
            signature,
            timestamp,
        )
        is True
    )


def test_verify_webhook_signature_rejects_wrong_signature(adapter):
    assert (
        adapter.verify_webhook_signature(
            b'{"type":"event"}',
            "wrong-signature",
            "1720000000000",
        )
        is False
    )


@pytest.mark.parametrize(
    ("payload", "signature", "timestamp"),
    [
        (b"{}", "", "1720000000000"),
        (b"{}", "signature", ""),
        (b"{}", "", ""),
    ],
)
def test_verify_webhook_signature_rejects_missing_inputs(
    adapter,
    payload,
    signature,
    timestamp,
):
    assert (
        adapter.verify_webhook_signature(
            payload,
            signature,
            timestamp,
        )
        is False
    )


def test_verify_webhook_signature_uses_secret_key_as_fallback(settings):
    settings.cashfree_webhook_secret = ""

    gateway = CashfreeSubscriptionAdapter(settings)
    timestamp = "1720000000000"
    raw_payload = b'{"type":"event"}'
    signature = generate_signature(
        "test-secret-key",
        timestamp,
        raw_payload,
    )

    assert (
        gateway.verify_webhook_signature(
            raw_payload,
            signature,
            timestamp,
        )
        is True
    )


# ---------------------------------------------------------------------------
# Create checkout session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_checkout_session_sends_expected_request(settings, plan):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/subscriptions")

        payload = json.loads(request.content)
        assert payload["customer_details"]["customer_id"] == "user-123"
        assert payload["customer_details"]["customer_email"] == "user@example.com"
        assert payload["plan_details"]["plan_id"] == plan.code
        assert payload["subscription_meta"]["return_url"] == ("https://example.com/payment/return")

        return httpx.Response(
            200,
            json={"subscription_session_id": "checkout-session-123"},
        )

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        subscription_id, session_id = await gateway.create_checkout_session(
            user_id="user-123",
            user_email="user@example.com",
            plan=plan,
            return_url="https://example.com/payment/return",
        )

    assert subscription_id.startswith("sub_")
    assert session_id == "checkout-session-123"


@pytest.mark.asyncio
async def test_create_checkout_session_uses_fallback_email(settings, plan):
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["customer_details"]["customer_email"] == ("user-123@effortless.app")
        return httpx.Response(200, json={"checkout_session_id": "session-456"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        subscription_id, session_id = await gateway.create_checkout_session(
            user_id="user-123",
            user_email=None,
            plan=plan,
            return_url="https://example.com/return",
        )

    assert subscription_id.startswith("sub_")
    assert session_id == "session-456"


@pytest.mark.asyncio
async def test_create_checkout_session_includes_first_charge_time(settings, plan):
    first_charge = datetime(
        2026,
        10,
        21,
        12,
        0,
        tzinfo=timezone(timedelta(hours=2)),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["subscription_first_charge_time"] == "2026-10-21T10:00:00Z"
        return httpx.Response(200, json={"subs_session_id": "session-789"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        _, session_id = await gateway.create_checkout_session(
            user_id="user-123",
            user_email="user@example.com",
            plan=plan,
            return_url="https://example.com/return",
            first_charge_time=first_charge,
        )

    assert session_id == "session-789"


@pytest.mark.asyncio
async def test_create_checkout_session_raises_on_api_error(settings, plan):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "Invalid subscription"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        with pytest.raises(SubscriptionPaymentError, match="creation failed"):
            await gateway.create_checkout_session(
                user_id="user-123",
                user_email="user@example.com",
                plan=plan,
                return_url="https://example.com/return",
            )


@pytest.mark.asyncio
async def test_create_checkout_session_rejects_missing_session_id(settings, plan):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "OK"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        with pytest.raises(SubscriptionPaymentError, match="session ID"):
            await gateway.create_checkout_session(
                user_id="user-123",
                user_email=None,
                plan=plan,
                return_url="https://example.com/return",
            )


@pytest.mark.asyncio
async def test_create_checkout_session_raises_on_network_error(settings, plan):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        with pytest.raises(SubscriptionPaymentError, match="Network error"):
            await gateway.create_checkout_session(
                user_id="user-123",
                user_email=None,
                plan=plan,
                return_url="https://example.com/return",
            )


@pytest.mark.asyncio
async def test_create_checkout_session_returns_mock_session(settings, plan):
    settings.cashfree_app_id = "test_mock_app"

    async with make_client(lambda request: httpx.Response(500)) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        subscription_id, session_id = await gateway.create_checkout_session(
            user_id="user-123",
            user_email=None,
            plan=plan,
            return_url="https://example.com/return",
        )

    assert subscription_id.startswith("sub_")
    assert session_id == f"session_mock_{subscription_id}"


# ---------------------------------------------------------------------------
# Cancel subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_subscription_sends_cancel_action(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/subscriptions/external-123/manage")
        assert json.loads(request.content) == {"action": "CANCEL"}
        return httpx.Response(200, json={"status": "OK"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        assert await gateway.cancel_subscription("external-123") is True


@pytest.mark.asyncio
async def test_cancel_subscription_returns_false_on_api_error(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "Cancellation rejected"})

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        assert await gateway.cancel_subscription("external-123") is False


@pytest.mark.asyncio
async def test_cancel_subscription_returns_false_on_network_error(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    async with make_client(handler) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        assert await gateway.cancel_subscription("external-123") is False


@pytest.mark.asyncio
async def test_cancel_subscription_returns_true_in_mock_mode(settings):
    settings.cashfree_app_id = "test_mock_app"

    async with make_client(lambda request: httpx.Response(500)) as client:
        gateway = CashfreeSubscriptionAdapter(settings, client=client)

        assert await gateway.cancel_subscription("external-123") is True
