"""Subscription entity and status lifecycle."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.value_objects.plan_snapshot import TierLimits


class SubscriptionStatus(StrEnum):
    """Provider-independent subscription lifecycle states."""

    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    PENDING = "PENDING"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CUSTOMER_CANCELLED = "CUSTOMER_CANCELLED"
    CUSTOMER_PAUSED = "CUSTOMER_PAUSED"
    LINK_EXPIRED = "LINK_EXPIRED"
    BANK_APPROVAL_PENDING = "BANK_APPROVAL_PENDING"
    CARD_EXPIRED = "CARD_EXPIRED"


class SubscriptionOperationType(StrEnum):
    """Operation that created a subscription."""

    NEW = "NEW"
    RENEWAL = "RENEWAL"
    UPGRADE = "UPGRADE"
    DOWNGRADE = "DOWNGRADE"


@dataclass(slots=True)
class Subscription:
    """User subscription entity with frozen plan entitlements."""

    user_id: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime

    id: UUID = field(default_factory=uuid4)
    plan_id: UUID | None = None
    provider: str = "cashfree"
    external_subscription_id: str | None = None
    external_customer_id: str | None = None
    cancelled_at: datetime | None = None
    is_active: bool = False
    operation_type: SubscriptionOperationType = SubscriptionOperationType.NEW
    related_subscription_id: UUID | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Frozen plan snapshot.
    snapshot_plan_name: str | None = None
    snapshot_max_seconds: int | None = None
    snapshot_max_usage_per_day: int | None = None
    snapshot_price: Decimal | None = None
    snapshot_currency: str | None = None

    def __post_init__(self) -> None:
        self.user_id = self.user_id.strip()
        self.provider = self.provider.strip().lower()

        if not self.user_id:
            raise ValueError("Subscription user_id must not be empty")

        if not self.provider:
            raise ValueError("Subscription provider must not be empty")

        if not isinstance(self.status, SubscriptionStatus):
            self.status = SubscriptionStatus(self.status)

        if not isinstance(
            self.operation_type,
            SubscriptionOperationType,
        ):
            self.operation_type = SubscriptionOperationType(self.operation_type)

        self._validate_datetime(
            self.current_period_start,
            "current_period_start",
        )
        self._validate_datetime(
            self.current_period_end,
            "current_period_end",
        )

        if self.current_period_end <= self.current_period_start:
            raise ValueError("current_period_end must be after current_period_start")

        if self.cancelled_at is not None:
            self._validate_datetime(self.cancelled_at, "cancelled_at")

        if self.snapshot_plan_name is not None:
            self.snapshot_plan_name = self.snapshot_plan_name.strip()

            if not self.snapshot_plan_name:
                raise ValueError("snapshot_plan_name must not be empty")

        if self.snapshot_max_seconds is not None and (
            isinstance(self.snapshot_max_seconds, bool)
            or not isinstance(self.snapshot_max_seconds, int)
            or self.snapshot_max_seconds <= 0
        ):
            raise ValueError("snapshot_max_seconds must be a positive integer")

        if self.snapshot_max_usage_per_day is not None and (
            isinstance(self.snapshot_max_usage_per_day, bool)
            or not isinstance(self.snapshot_max_usage_per_day, int)
            or self.snapshot_max_usage_per_day <= 0
        ):
            raise ValueError("snapshot_max_usage_per_day must be a positive integer")

        if self.snapshot_price is not None:
            if not isinstance(self.snapshot_price, Decimal):
                raise TypeError("snapshot_price must be a Decimal")

            if not self.snapshot_price.is_finite() or self.snapshot_price < 0:
                raise ValueError("snapshot_price must be finite and non-negative")

        if self.snapshot_currency is not None:
            self.snapshot_currency = self.snapshot_currency.strip().upper()

            if len(self.snapshot_currency) != 3 or not self.snapshot_currency.isalpha():
                raise ValueError("snapshot_currency must be a three-letter code")

    @staticmethod
    def _validate_datetime(value: datetime, field_name: str) -> None:
        """Require timezone-aware datetimes."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")

    @property
    def limits(self) -> TierLimits:
        """Return frozen usage limits for this subscription."""
        if self.snapshot_max_seconds is None or self.snapshot_max_usage_per_day is None:
            raise ValueError("Subscription does not have a complete plan snapshot")

        return TierLimits(
            max_seconds_per_request=self.snapshot_max_seconds,
            max_usage_per_day=self.snapshot_max_usage_per_day,
        )

    def is_currently_active(
        self,
        now: datetime | None = None,
    ) -> bool:
        """Check whether this subscription grants access at a given time."""
        current_time = now or datetime.now(UTC)
        self._validate_datetime(current_time, "now")

        if not self.is_active:
            return False

        if self.status != SubscriptionStatus.ACTIVE:
            return False

        return self.current_period_start <= current_time < self.current_period_end
