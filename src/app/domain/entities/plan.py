"""Subscription plan entity and billing specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class BillingPeriod(StrEnum):
    """Supported billing intervals."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

    @classmethod
    def from_str(
        cls,
        value: str | BillingPeriod,
    ) -> BillingPeriod:
        """Normalize supported billing-period aliases."""
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

        valid_options = ", ".join(period.value for period in cls)
        raise ValueError(f"Invalid billing period '{value}'. Supported values: {valid_options}.")

    @property
    def duration_days(self) -> int:
        """Return approximate duration in days."""
        durations = {
            BillingPeriod.DAILY: 1,
            BillingPeriod.WEEKLY: 7,
            BillingPeriod.MONTHLY: 30,
            BillingPeriod.YEARLY: 365,
        }
        return durations[self]


@dataclass(slots=True)
class Plan:
    """Mutable subscription plan entity."""

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

    has_trial: bool = False
    trial_duration_days: int | None = None

    def __post_init__(self) -> None:
        self.code = self.code.strip()
        self.name = self.name.strip()
        self.currency = self.currency.strip().upper()

        if not self.code:
            raise ValueError("Plan code must not be empty")

        if not self.name:
            raise ValueError("Plan name must not be empty")

        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("Currency must be a three-letter code")

        if not isinstance(self.actual_price, Decimal):
            raise TypeError("actual_price must be a Decimal")

        if not isinstance(self.offer_price, Decimal):
            raise TypeError("offer_price must be a Decimal")

        if not self.actual_price.is_finite():
            raise ValueError("actual_price must be finite")

        if not self.offer_price.is_finite():
            raise ValueError("offer_price must be finite")

        if self.actual_price < 0 or self.offer_price < 0:
            raise ValueError("Plan prices must not be negative")

        if self.offer_price > self.actual_price:
            raise ValueError("offer_price must not exceed actual_price")

        self.billing_period = BillingPeriod.from_str(self.billing_period)

        if (
            isinstance(self.max_seconds_per_request, bool)
            or not isinstance(self.max_seconds_per_request, int)
            or self.max_seconds_per_request <= 0
        ):
            raise ValueError("max_seconds_per_request must be a positive integer")

        if (
            isinstance(self.max_usage_per_day, bool)
            or not isinstance(self.max_usage_per_day, int)
            or self.max_usage_per_day <= 0
        ):
            raise ValueError("max_usage_per_day must be a positive integer")
