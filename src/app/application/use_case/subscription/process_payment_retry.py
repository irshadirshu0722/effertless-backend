from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities.payment_retry import (
    PaymentRetryStatus,
)
from app.domain.entities.subscription import SubscriptionStatus
from app.ports.repository import SubscriptionRepository
from app.ports.repository.payment_retry_repository import (
    PaymentRetryRepository,
)
from app.ports.services import PaymentGateway


class ProcessPaymentRetryUseCase:
    def __init__(
        self,
        payment_retry_repo: PaymentRetryRepository,
        subscription_repo: SubscriptionRepository,
        payment_gateway: PaymentGateway,
    ) -> None:
        self._payment_retry_repo = payment_retry_repo
        self._subscription_repo = subscription_repo
        self._payment_gateway = payment_gateway

    async def execute(self, retry_id: UUID) -> None:
        retry = await self._payment_retry_repo.get_by_id(retry_id)

        if retry is None:
            return

        if retry.status is not PaymentRetryStatus.SCHEDULED:
            return

        now = datetime.now(UTC)

        if retry.next_retry_at is None or retry.next_retry_at > now:
            return

        subscription = await self._subscription_repo.get_by_id(retry.subscription_id)

        if subscription is None:
            retry.cancel()
            await self._payment_retry_repo.save(retry)
            return

        if subscription.status in {
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.CUSTOMER_CANCELLED,
            SubscriptionStatus.EXPIRED,
            SubscriptionStatus.COMPLETED,
        }:
            retry.cancel()
            await self._payment_retry_repo.save(retry)
            return

        retry.start_attempt()
        await self._payment_retry_repo.save(retry)

        try:
            payment_attempt_id = await self._payment_gateway.retry_subscription_payment(
                external_subscription_id=(subscription.external_subscription_id),
                idempotency_key=f"payment-retry:{retry.id}:{retry.retry_count + 1}",
            )
        except Exception as exc:
            retry.last_error = f"Retry outcome requires reconciliation: {type(exc).__name__}"
            retry.updated_at = datetime.now(UTC)
            await self._payment_retry_repo.save(retry)
            raise

        # The provider has accepted/created the attempt. This is NOT
        # confirmation that payment succeeded. Wait for its webhook.
        retry.last_payment_attempt_id = payment_attempt_id
        retry.updated_at = datetime.now(UTC)
        await self._payment_retry_repo.save(retry)
