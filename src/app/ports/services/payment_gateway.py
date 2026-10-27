"""Payment gateway port for subscription billing."""

from datetime import datetime
from typing import Protocol

from app.domain.entities.plan import Plan


class PaymentGateway(Protocol):
    """Minimal async payment gateway contract used by application services."""

    async def create_plan(self, plan: Plan) -> bool:
        """Create a recurring billing plan with the payment provider."""

    async def delete_plan(self, plan_code: str) -> bool:
        """Delete a recurring billing plan from the payment provider."""

    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str | None,
        plan: Plan,
        return_url: str,
        first_charge_time: datetime | None = None,
    ) -> tuple[str, str]:
        """Create a subscription checkout session.

        Returns:
            A tuple containing the external subscription ID and checkout
            session ID.
        """

    async def cancel_subscription(
        self,
        external_subscription_id: str,
    ) -> bool:
        """Request cancellation of an external subscription."""

    def verify_webhook_signature(
        self,
        raw_payload: bytes,
        signature: str,
        timestamp: str,
    ) -> bool:
        """Verify the authenticity of a payment provider webhook."""

    async def retry_subscription_payment(
        self,
        external_subscription_id: str,
        idempotency_key: str,
    ) -> str:
        """Initiate a supported retry and return its payment-attempt ID."""
