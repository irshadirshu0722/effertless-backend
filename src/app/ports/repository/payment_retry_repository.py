from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.entities.payment_retry import PaymentRetry


class PaymentRetryRepository(Protocol):
    async def save(self, retry: PaymentRetry) -> PaymentRetry:
        """Create or update a retry workflow."""
        ...

    async def get_by_id(self, retry_id: UUID) -> PaymentRetry | None: ...

    async def get_by_subscription_and_period(
        self,
        subscription_id: UUID,
        billing_period_start: datetime,
    ) -> PaymentRetry | None: ...

    async def list_due(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[PaymentRetry]:
        """Return scheduled retries whose next_retry_at is due."""
        ...
