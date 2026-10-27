from datetime import UTC, datetime
from uuid import UUID

from app.adapters.tasks.payment_retry import process_payment_retry
from app.ports.services.payment_retry_scheduler import (
    PaymentRetryScheduler,
)


class CeleryPaymentRetryScheduler(PaymentRetryScheduler):
    def schedule_retry(
        self,
        retry_id: UUID,
        run_at: datetime,
    ) -> None:
        if run_at.tzinfo is None:
            raise ValueError("run_at must be timezone-aware")

        eta = run_at.astimezone(UTC)

        process_payment_retry.apply_async(
            args=[str(retry_id)],
            eta=eta,
        )

    def enqueue_retry(self, retry_id: UUID) -> None:
        process_payment_retry.delay(str(retry_id))
