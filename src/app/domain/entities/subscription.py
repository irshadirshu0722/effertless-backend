"""Subscription entity and status lifecycle."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.value_objects.plan_snapshot import PlanSnapshot, TierLimits


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"
    SCHEDULED = "scheduled"


@dataclass(frozen=True, slots=True)
class Subscription:
    """Immutable user subscription entity managing access and frozen quota."""

    user_id: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    snapshot: PlanSnapshot
    id: UUID = field(default_factory=uuid4)
    plan_id: UUID | None = None
    provider: str = "cashfree"
    external_subscription_id: str | None = None
    external_customer_id: str | None = None
    cancelled_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise ValueError("Subscription user_id must not be empty")

    @property
    def limits(self) -> TierLimits:
        return self.snapshot.limits

    def is_currently_active(self, now: datetime | None = None) -> bool:
        """Check if subscription grants active access at given time."""
        current_time = now or datetime.now(UTC)
        if self.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
            return False
        return self.current_period_start <= current_time <= self.current_period_end
