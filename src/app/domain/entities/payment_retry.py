from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class PaymentRetryStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    EXHAUSTED = "EXHAUSTED"
    CANCELLED = "CANCELLED"


@dataclass
class PaymentRetry:
    id: UUID
    subscription_id: UUID
    billing_period_start: datetime
    retry_count: int
    max_retries: int
    next_retry_at: datetime | None
    status: PaymentRetryStatus
    last_payment_attempt_id: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        subscription_id: UUID,
        billing_period_start: datetime,
        next_retry_at: datetime,
        max_retries: int = 3,
    ) -> "PaymentRetry":
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1")

        if billing_period_start.tzinfo is None:
            raise ValueError("billing_period_start must be timezone-aware")

        if next_retry_at.tzinfo is None:
            raise ValueError("next_retry_at must be timezone-aware")

        now = datetime.now(UTC)

        return cls(
            id=uuid4(),
            subscription_id=subscription_id,
            billing_period_start=billing_period_start,
            retry_count=0,
            max_retries=max_retries,
            next_retry_at=next_retry_at,
            status=PaymentRetryStatus.SCHEDULED,
            last_payment_attempt_id=None,
            last_error=None,
            created_at=now,
            updated_at=now,
        )

    def start_attempt(self) -> None:
        if self.status != PaymentRetryStatus.SCHEDULED:
            raise ValueError("Only scheduled retries can be started")

        if self.retry_count >= self.max_retries:
            raise ValueError("Maximum retry attempts have been reached")

        self.status = PaymentRetryStatus.IN_PROGRESS
        self.next_retry_at = None
        self.updated_at = datetime.now(UTC)

    def record_failure(
        self,
        *,
        error: str,
        next_retry_at: datetime | None,
        payment_attempt_id: str | None = None,
    ) -> None:
        if self.status != PaymentRetryStatus.IN_PROGRESS:
            raise ValueError("A retry must be in progress to record its result")

        self.retry_count += 1
        self.last_error = error
        self.last_payment_attempt_id = payment_attempt_id
        self.updated_at = datetime.now(UTC)

        if self.retry_count >= self.max_retries:
            self.status = PaymentRetryStatus.EXHAUSTED
            self.next_retry_at = None
            return

        if next_retry_at is None:
            raise ValueError("next_retry_at is required when retries remain")

        if next_retry_at.tzinfo is None:
            raise ValueError("next_retry_at must be timezone-aware")

        self.status = PaymentRetryStatus.SCHEDULED
        self.next_retry_at = next_retry_at

    def mark_succeeded(
        self,
        *,
        payment_attempt_id: str | None = None,
    ) -> None:
        if self.status in {
            PaymentRetryStatus.EXHAUSTED,
            PaymentRetryStatus.CANCELLED,
        }:
            raise ValueError("Cannot mark an exhausted or cancelled retry as succeeded")

        self.status = PaymentRetryStatus.SUCCEEDED
        self.next_retry_at = None
        self.last_error = None

        if payment_attempt_id is not None:
            self.last_payment_attempt_id = payment_attempt_id

        self.updated_at = datetime.now(UTC)

    def cancel(self) -> None:
        if self.status in {
            PaymentRetryStatus.SUCCEEDED,
            PaymentRetryStatus.EXHAUSTED,
            PaymentRetryStatus.CANCELLED,
        }:
            return

        self.status = PaymentRetryStatus.CANCELLED
        self.next_retry_at = None
        self.updated_at = datetime.now(UTC)
