"""Unit tests for Cashfree subscription adapter."""

import base64
import hashlib
import hmac
from decimal import Decimal

import pytest

from app.adapters.cashfree import CashfreeSubscriptionAdapter
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
    settings = Settings(cashfree_secret_key=secret)
    adapter = CashfreeSubscriptionAdapter(settings)

    payload = b'{"event":"SUBSCRIPTION_ACTIVATION","data":{"subscription_id":"sub_1"}}'
    timestamp = "1728000000"

    message = timestamp.encode("utf-8") + payload
    valid_sig = base64.b64encode(
        hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    ).decode("utf-8")

    assert adapter.verify_webhook_signature(payload, valid_sig, timestamp) is True


def test_verify_webhook_signature_tampered_or_invalid() -> None:
    settings = Settings(cashfree_secret_key="secret-key-123")
    adapter = CashfreeSubscriptionAdapter(settings)

    payload = b'{"event":"SUBSCRIPTION_ACTIVATION"}'
    assert adapter.verify_webhook_signature(payload, "bad_signature", "1728000000") is False
    assert adapter.verify_webhook_signature(payload, "", "1728000000") is False
    assert adapter.verify_webhook_signature(payload, "sig", "") is False


@pytest.mark.asyncio
async def test_create_checkout_session_mock_fallback(test_plan: Plan) -> None:
    settings = Settings(cashfree_app_id="", cashfree_secret_key="")
    adapter = CashfreeSubscriptionAdapter(settings)

    sub_id, link = await adapter.create_checkout_session(
        user_id="user-1",
        user_email="user1@example.com",
        plan=test_plan,
        return_url="https://return.url",
    )

    assert sub_id.startswith("sub_")
    assert sub_id in link
