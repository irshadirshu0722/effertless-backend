"""Cashfree payment gateway adapter for subscriptions."""

import base64
import hashlib
import hmac
import uuid

import httpx

from app.core.config import Settings
from app.core.exceptions import SubscriptionPaymentError
from app.domain.entities.plan import Plan
from app.ports.subscription import PaymentGateway


class CashfreeSubscriptionAdapter(PaymentGateway):
    """Adapter integrating with Cashfree Subscriptions & Payment APIs."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._base_url = (
            "https://api.cashfree.com/pg"
            if settings.cashfree_environment.lower() == "production"
            else "https://sandbox.cashfree.com/pg"
        )

    def _get_secret(self) -> str:
        return self._settings.cashfree_webhook_secret or self._settings.cashfree_secret_key

    def verify_webhook_signature(
        self,
        raw_payload: bytes,
        signature: str,
        timestamp: str,
    ) -> bool:
        """Verify HMAC SHA-256 signature for incoming Cashfree webhooks."""
        secret = self._get_secret()
        if not secret or not signature or not timestamp:
            return False

        message = timestamp.encode("utf-8") + raw_payload
        computed = base64.b64encode(
            hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
        ).decode("utf-8")

        return hmac.compare_digest(computed, signature)

    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str | None,
        plan: Plan,
        return_url: str,
    ) -> tuple[str, str]:
        """Create a Cashfree subscription session."""
        subscription_id = f"sub_{uuid.uuid4().hex[:16]}"
        headers = {
            "x-client-id": self._settings.cashfree_app_id,
            "x-client-secret": self._settings.cashfree_secret_key,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json",
        }
        payload = {
            "subscription_id": subscription_id,
            "customer_details": {
                "customer_id": user_id,
                "customer_email": user_email or f"{user_id}@effortless.app",
                "customer_phone": "9999999999",
            },
            "plan_details": {
                "plan_id": plan.code,
                "plan_name": plan.name,
                "plan_type": "PERIODIC",
                "plan_currency": plan.currency,
                "plan_amount": float(plan.offer_price),
                "plan_interval_type": plan.billing_period.upper(),
                "plan_intervals": 1,
            },
            "subscription_meta": {
                "return_url": return_url,
            },
        }

        # If dummy, not configured, or test credentials, return a mock session link
        if (
            not self._settings.cashfree_app_id
            or not self._settings.cashfree_secret_key
            or self._settings.cashfree_app_id.startswith("test_")
        ):
            return subscription_id, f"https://mock.cashfree.com/checkout/{subscription_id}"

        async with self._client or httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/subscriptions",
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )
            except httpx.RequestError as exc:
                raise SubscriptionPaymentError(
                    f"Network error connecting to Cashfree: {exc}"
                ) from exc

            if response.status_code >= 400:
                raise SubscriptionPaymentError(
                    f"Cashfree subscription creation failed: {response.text}"
                )

            data = response.json()
            payment_link = (
                data.get("sub_link")
                or data.get("payment_link")
                or f"https://payments.cashfree.com/sub/{subscription_id}"
            )
            return subscription_id, payment_link

    async def cancel_subscription(self, external_subscription_id: str) -> bool:
        """Cancel subscription on Cashfree."""
        if (
            not self._settings.cashfree_app_id
            or not self._settings.cashfree_secret_key
            or self._settings.cashfree_app_id.startswith("test_")
        ):
            return True

        headers = {
            "x-client-id": self._settings.cashfree_app_id,
            "x-client-secret": self._settings.cashfree_secret_key,
            "x-api-version": "2023-08-01",
        }
        async with self._client or httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/subscriptions/{external_subscription_id}/cancel",
                    headers=headers,
                    timeout=10.0,
                )
                return response.status_code < 400
            except httpx.RequestError:
                return False
