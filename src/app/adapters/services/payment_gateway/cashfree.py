"""Cashfree payment gateway adapter for subscriptions."""

import base64
import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import SubscriptionPaymentError
from app.domain.entities.plan import BillingPeriod, Plan
from app.ports.services.payment_gateway import PaymentGateway

logger = logging.getLogger("app.payments.cashfree")


class CashfreePlanIntervalType(StrEnum):
    """Supported interval types for recurring plans."""

    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"


_BILLING_PERIOD_TO_CASHFREE_INTERVAL: dict[BillingPeriod, CashfreePlanIntervalType] = {
    BillingPeriod.DAILY: CashfreePlanIntervalType.DAY,
    BillingPeriod.WEEKLY: CashfreePlanIntervalType.WEEK,
    BillingPeriod.MONTHLY: CashfreePlanIntervalType.MONTH,
    BillingPeriod.YEARLY: CashfreePlanIntervalType.YEAR,
}


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

        logger.info(
            "Cashfree adapter initialized: environment=%s base_url=%s mock_mode=%s",
            settings.cashfree_environment,
            self._base_url,
            self._is_mock_mode(),
        )

    def _get_secret(self) -> str:
        return self._settings.cashfree_webhook_secret or self._settings.cashfree_secret_key

    def _is_mock_mode(self) -> bool:
        return (
            not self._settings.cashfree_app_id
            or not self._settings.cashfree_secret_key
            or self._settings.cashfree_app_id.startswith("test_")
        )

    def _headers(
        self,
        *,
        include_content_type: bool = False,
    ) -> dict[str, str]:
        headers = {
            "x-client-id": self._settings.cashfree_app_id,
            "x-client-secret": self._settings.cashfree_secret_key,
            "x-api-version": "2025-01-01",
        }

        if include_content_type:
            headers["Content-Type"] = "application/json"

        return headers

    @staticmethod
    def _first_charge_time_for_cashfree(
        first_charge_time: datetime,
    ) -> str:
        first_charge_utc = (
            first_charge_time
            if first_charge_time.tzinfo is not None
            else first_charge_time.replace(tzinfo=UTC)
        ).astimezone(UTC)

        formatted = first_charge_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.debug(
            "Normalized Cashfree first charge time: input=%s output_utc=%s",
            first_charge_time.isoformat(),
            formatted,
        )

        return formatted

    def _plan_payload(self, plan: Plan) -> dict[str, Any]:
        period = BillingPeriod.from_str(plan.billing_period)
        interval_type = _BILLING_PERIOD_TO_CASHFREE_INTERVAL[period].value

        payload = {
            "plan_id": plan.code,
            "plan_name": plan.name,
            "plan_type": "PERIODIC",
            "plan_currency": plan.currency,
            "plan_recurring_amount": float(plan.offer_price),
            "plan_max_amount": float(plan.offer_price),
            "plan_intervals": 1,
            "plan_interval_type": interval_type,
            "plan_note": f"Effortless plan {plan.code}",
        }

        logger.debug(
            "Cashfree plan payload prepared: plan_id=%s "
            "billing_period=%s interval_type=%s currency=%s",
            plan.code,
            plan.billing_period,
            interval_type,
            plan.currency,
        )

        return payload

    async def create_plan(self, plan: Plan) -> bool:
        """Create a plan in Cashfree."""

        logger.info(
            "Creating Cashfree plan: plan_id=%s",
            plan.code,
        )

        if self._is_mock_mode():
            logger.warning(
                "Cashfree mock mode enabled; skipping plan creation: plan_id=%s",
                plan.code,
            )
            return True

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            try:
                response = await client.post(
                    f"{self._base_url}/plans",
                    json=self._plan_payload(plan),
                    headers=self._headers(include_content_type=True),
                    timeout=10.0,
                )

                logger.info(
                    "Cashfree create-plan response: plan_id=%s http_status=%s",
                    plan.code,
                    response.status_code,
                )

            except httpx.RequestError as error:
                logger.exception(
                    "Network error creating Cashfree plan: plan_id=%s",
                    plan.code,
                )
                raise SubscriptionPaymentError("Network error creating Cashfree plan") from error

            if response.status_code >= 400:
                logger.error(
                    "Cashfree plan creation failed: plan_id=%s http_status=%s response=%s",
                    plan.code,
                    response.status_code,
                    response.text[:2000],
                )
                raise SubscriptionPaymentError(
                    f"Cashfree plan creation failed: {response.text}"
                ) from httpx.RequestError

            logger.info(
                "Cashfree plan created successfully: plan_id=%s",
                plan.code,
            )
            return True

        finally:
            if should_close:
                await client.aclose()

    async def delete_plan(self, plan_code: str) -> bool:
        """Delete a plan from Cashfree."""

        logger.info(
            "Deleting Cashfree plan: plan_id=%s",
            plan_code,
        )

        if self._is_mock_mode():
            logger.warning(
                "Cashfree mock mode enabled; skipping plan deletion: plan_id=%s",
                plan_code,
            )
            return True

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            try:
                response = await client.delete(
                    f"{self._base_url}/plans/{plan_code}",
                    headers=self._headers(),
                    timeout=10.0,
                )

                logger.info(
                    "Cashfree delete-plan response: plan_id=%s http_status=%s",
                    plan_code,
                    response.status_code,
                )

            except httpx.RequestError as err:
                logger.exception(
                    "Network error deleting Cashfree plan: plan_id=%s",
                    plan_code,
                )
                raise SubscriptionPaymentError("Network error deleting Cashfree plan") from err

            if response.status_code == 404:
                logger.info(
                    "Cashfree plan already absent: plan_id=%s",
                    plan_code,
                )
                return True

            if response.status_code >= 400:
                logger.error(
                    "Cashfree plan deletion failed: plan_id=%s http_status=%s response=%s",
                    plan_code,
                    response.status_code,
                    response.text[:2000],
                )
                raise SubscriptionPaymentError(f"Cashfree plan deletion failed: {response.text}")

            logger.info(
                "Cashfree plan deleted successfully: plan_id=%s",
                plan_code,
            )
            return True

        finally:
            if should_close:
                await client.aclose()

    def verify_webhook_signature(
        self,
        raw_payload: bytes,
        signature: str,
        timestamp: str,
    ) -> bool:
        """Verify HMAC SHA-256 signature for Cashfree webhooks."""

        secret = self._get_secret()

        if not secret or not signature or not timestamp:
            logger.warning(
                "Cashfree webhook signature verification failed: missing required signature inputs"
            )
            return False

        message = timestamp.encode("utf-8") + raw_payload

        computed = base64.b64encode(
            hmac.new(
                secret.encode("utf-8"),
                message,
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        is_valid = hmac.compare_digest(computed, signature)

        if is_valid:
            logger.debug("Cashfree webhook signature verified")
        else:
            logger.warning("Cashfree webhook signature verification failed: signature mismatch")

        return is_valid

    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str | None,
        plan: Plan,
        return_url: str,
        first_charge_time: datetime | None = None,
    ) -> tuple[str, str]:
        """Create a Cashfree subscription checkout session."""

        subscription_id = f"sub_{uuid.uuid4().hex[:16]}"
        period = BillingPeriod.from_str(plan.billing_period)
        interval_type = _BILLING_PERIOD_TO_CASHFREE_INTERVAL[period].value

        logger.info(
            "Creating Cashfree subscription: subscription_id=%s "
            "user_id=%s plan_id=%s amount=%s currency=%s "
            "interval_type=%s first_charge_time=%s",
            subscription_id,
            user_id,
            plan.code,
            plan.offer_price,
            plan.currency,
            interval_type,
            (first_charge_time.isoformat() if first_charge_time else "provider_default"),
        )

        payload: dict[str, Any] = {
            "subscription_id": subscription_id,
            "customer_details": {
                "customer_id": user_id,
                "customer_email": (user_email or f"{user_id}@effortless.app"),
                "customer_phone": "9999999999",
            },
            "plan_details": {
                "plan_id": plan.code,
                "plan_name": plan.name,
                "plan_type": "PERIODIC",
                "plan_currency": plan.currency,
                "plan_amount": float(plan.offer_price),
                "plan_interval_type": interval_type,
                "plan_intervals": 1,
            },
            "subscription_meta": {
                "return_url": return_url,
            },
        }

        if first_charge_time is not None:
            normalized_charge_time = self._first_charge_time_for_cashfree(first_charge_time)
            payload["subscription_first_charge_time"] = normalized_charge_time

            logger.info(
                "Cashfree first charge scheduled: subscription_id=%s first_charge_time=%s",
                subscription_id,
                normalized_charge_time,
            )
        else:
            logger.info(
                "No explicit first charge time supplied; "
                "Cashfree will apply its configured/default behavior: "
                "subscription_id=%s",
                subscription_id,
            )

        if self._is_mock_mode():
            logger.warning(
                "Cashfree mock mode enabled; returning mock checkout session: subscription_id=%s",
                subscription_id,
            )
            return subscription_id, f"session_mock_{subscription_id}"

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            try:
                response = await client.post(
                    f"{self._base_url}/subscriptions",
                    json=payload,
                    headers=self._headers(include_content_type=True),
                    timeout=10.0,
                )

                logger.info(
                    "Cashfree create-subscription response: subscription_id=%s http_status=%s",
                    subscription_id,
                    response.status_code,
                )

            except httpx.RequestError as err:
                logger.exception(
                    "Network error creating Cashfree subscription: subscription_id=%s",
                    subscription_id,
                )
                raise SubscriptionPaymentError("Network error connecting to Cashfree") from err

            if response.status_code >= 400:
                logger.error(
                    "Cashfree subscription creation failed: "
                    "subscription_id=%s http_status=%s response=%s",
                    subscription_id,
                    response.status_code,
                    response.text[:2000],
                )
                raise SubscriptionPaymentError(
                    f"Cashfree subscription creation failed: {response.text}"
                )

            data = response.json()

            checkout_session_id = (
                data.get("subscription_session_id")
                or data.get("checkout_session_id")
                or data.get("subs_session_id")
            )

            if not checkout_session_id:
                logger.error(
                    "Cashfree response missing checkout session ID: "
                    "subscription_id=%s response_keys=%s",
                    subscription_id,
                    list(data.keys()),
                )
                raise SubscriptionPaymentError(
                    "Cashfree response did not include a checkout session ID"
                )

            logger.info(
                "Cashfree subscription checkout session created: subscription_id=%s",
                subscription_id,
            )

            # Do not log the checkout session token.
            return subscription_id, str(checkout_session_id)

        finally:
            if should_close:
                await client.aclose()

    async def cancel_subscription(
        self,
        external_subscription_id: str,
    ) -> bool:
        """Cancel a subscription using Cashfree's Manage Subscription API."""

        logger.info(
            "Requesting Cashfree subscription cancellation: subscription_id=%s",
            external_subscription_id,
        )

        if self._is_mock_mode():
            logger.warning(
                "Mock mode: skipping Cashfree cancellation: subscription_id=%s",
                external_subscription_id,
            )
            return True

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            try:
                response = await client.post(
                    (f"{self._base_url}/subscriptions/{external_subscription_id}/manage"),
                    json={"action": "CANCEL"},
                    headers=self._headers(include_content_type=True),
                    timeout=10.0,
                )
            except httpx.RequestError:
                logger.exception(
                    "Cashfree cancellation request failed: subscription_id=%s",
                    external_subscription_id,
                )
                return False

            if response.status_code >= 400:
                logger.error(
                    "Cashfree cancellation rejected: subscription_id=%s http_status=%s response=%s",
                    external_subscription_id,
                    response.status_code,
                    response.text[:2000],
                )
                return False

            logger.info(
                "Cashfree cancellation request accepted: subscription_id=%s http_status=%s",
                external_subscription_id,
                response.status_code,
            )
            return True

        finally:
            if should_close:
                await client.aclose()
