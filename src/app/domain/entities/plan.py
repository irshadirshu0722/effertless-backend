"""Subscription plan entity and value specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class BillingPeriod(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

    @classmethod
    def from_str(cls, value: str | BillingPeriod) -> BillingPeriod:
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        mapping = {
            "daily": cls.DAILY,
            "day": cls.DAILY,
            "weekly": cls.WEEKLY,
            "week": cls.WEEKLY,
            "monthly": cls.MONTHLY,
            "month": cls.MONTHLY,
            "yearly": cls.YEARLY,
            "year": cls.YEARLY,
        }
        if normalized in mapping:
            return mapping[normalized]
        valid_options = ", ".join(cls)
        raise ValueError(f"Invalid billing period '{value}'. Supported values: {valid_options}.")

    @property
    def duration_days(self) -> int:
        if self == BillingPeriod.DAILY:
            return 1
        if self == BillingPeriod.WEEKLY:
            return 7
        if self == BillingPeriod.YEARLY:
            return 365
        return 30


@dataclass(frozen=True, slots=True)
class Plan:
    """Immutable plan entity defining subscription tier limits and pricing."""

    code: str
    name: str
    billing_period: BillingPeriod | str
    actual_price: Decimal
    offer_price: Decimal
    max_seconds_per_request: int
    max_usage_per_day: int
    id: UUID = field(default_factory=uuid4)
    currency: str = "INR"
    is_active: bool = True
    is_deleted: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("Plan code must not be empty")
        if not self.name.strip():
            raise ValueError("Plan name must not be empty")
        validated_period = BillingPeriod.from_str(self.billing_period)
        object.__setattr__(self, "billing_period", validated_period)
        if self.max_seconds_per_request <= 0:
            raise ValueError("max_seconds_per_request must be positive")
        if self.max_usage_per_day <= 0:
            raise ValueError("max_usage_per_day must be positive")
        if self.actual_price < 0 or self.offer_price < 0:
            raise ValueError("Plan prices must not be negative")
