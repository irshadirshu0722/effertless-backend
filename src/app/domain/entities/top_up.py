"""Top-up purchase entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class TopUpStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class TopUp:
    """A user's purchase of additional credit seconds."""

    user_id: str
    seconds: int
    amount: Decimal
    currency: str = "INR"

    id: UUID = field(default_factory=uuid4)
    status: TopUpStatus = TopUpStatus.PENDING
    provider: str = "cashfree"
    external_payment_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.user_id = self.user_id.strip()
        self.provider = self.provider.strip().lower()
        self.currency = self.currency.strip().upper()

        if not self.user_id:
            raise ValueError("user_id cannot be empty")

        if not self.provider:
            raise ValueError("provider cannot be empty")

        if isinstance(self.seconds, bool) or not isinstance(self.seconds, int) or self.seconds <= 0:
            raise ValueError("seconds must be a positive integer")

        if isinstance(self.amount, bool):
            raise ValueError("amount must be a valid positive amount")

        try:
            self.amount = Decimal(str(self.amount))
        except (ValueError, TypeError, ArithmeticError) as exc:
            raise ValueError("amount must be a valid positive amount") from exc

        if not self.amount.is_finite() or self.amount <= 0:
            raise ValueError("amount must be a valid positive amount")

        try:
            self.status = TopUpStatus(self.status)
        except ValueError as exc:
            raise ValueError("invalid top-up status") from exc

        if len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isalpha():
            raise ValueError("currency must be a three-letter currency code")

        for field_name in ("created_at", "updated_at", "completed_at"):
            value = getattr(self, field_name)
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{field_name} must be timezone-aware")

        if self.status is TopUpStatus.COMPLETED and self.completed_at is None:
            self.completed_at = self.updated_at

    def complete(self, external_payment_id: str | None = None) -> None:
        """Mark the purchase completed after verified payment."""
        if self.status is not TopUpStatus.PENDING:
            raise ValueError("only pending top-ups can be completed")

        if external_payment_id is not None:
            external_payment_id = external_payment_id.strip()
            if not external_payment_id:
                raise ValueError("external_payment_id cannot be empty")
            self.external_payment_id = external_payment_id

        now = datetime.now(UTC)
        self.status = TopUpStatus.COMPLETED
        self.completed_at = now
        self.updated_at = now

    def fail(self) -> None:
        """Mark a pending purchase as failed."""
        if self.status is not TopUpStatus.PENDING:
            raise ValueError("only pending top-ups can fail")

        self.status = TopUpStatus.FAILED
        self.updated_at = datetime.now(UTC)

    def cancel(self) -> None:
        """Cancel a pending purchase."""
        if self.status is not TopUpStatus.PENDING:
            raise ValueError("only pending top-ups can be cancelled")

        self.status = TopUpStatus.CANCELLED
        self.updated_at = datetime.now(UTC)
