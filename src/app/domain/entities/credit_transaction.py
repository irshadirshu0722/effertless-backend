"""Immutable credit transaction ledger entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class CreditTransactionType(StrEnum):
    SUBSCRIPTION_GRANTED = "SUBSCRIPTION_GRANTED"
    TOP_UP_PURCHASED = "TOP_UP_PURCHASED"
    SUBSCRIPTION_CONSUMED = "SUBSCRIPTION_CONSUMED"
    TOP_UP_CONSUMED = "TOP_UP_CONSUMED"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"
    ADJUSTMENT = "ADJUSTMENT"
    TRAIL_GRANTED = "TRAIL_GRANTED"


@dataclass(frozen=True, slots=True)
class CreditTransaction:
    """An immutable record of a credit balance change."""

    user_id: str
    transaction_type: CreditTransactionType
    subscription_delta: int
    top_up_delta: int
    subscription_balance_after: int
    top_up_balance_after: int

    id: UUID = field(default_factory=uuid4)
    credit_id: UUID | None = None
    reference_id: UUID | None = None
    description: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise ValueError("user_id cannot be empty")

        try:
            transaction_type = CreditTransactionType(self.transaction_type)
        except ValueError as exc:
            raise ValueError("invalid credit transaction type") from exc

        object.__setattr__(self, "user_id", self.user_id.strip())
        object.__setattr__(self, "transaction_type", transaction_type)

        for field_name in (
            "subscription_delta",
            "top_up_delta",
            "subscription_balance_after",
            "top_up_balance_after",
        ):
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{field_name} must be an integer")

        if self.subscription_delta == 0 and self.top_up_delta == 0:
            raise ValueError("transaction must change at least one balance")

        if self.subscription_balance_after < 0:
            raise ValueError("subscription balance cannot be negative")

        if self.top_up_balance_after < 0:
            raise ValueError("top-up balance cannot be negative")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        if self.description is not None:
            object.__setattr__(self, "description", self.description.strip())
