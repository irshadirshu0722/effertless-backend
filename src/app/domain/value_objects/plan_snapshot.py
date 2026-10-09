"""Frozen plan snapshot and tier limits value objects."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TierLimits:
    """Configured limits for a tier."""

    max_seconds_per_request: int
    max_usage_per_day: int


@dataclass(frozen=True, slots=True)
class PlanSnapshot:
    """Immutable snapshot of plan terms frozen at subscription creation."""

    plan_name: str
    max_seconds_per_request: int
    max_usage_per_day: int
    price: Decimal
    currency: str = "INR"

    def __post_init__(self) -> None:
        if not self.plan_name.strip():
            raise ValueError("Snapshot plan name must not be empty")
        if self.max_seconds_per_request <= 0:
            raise ValueError("Snapshot max seconds must be positive")
        if self.max_usage_per_day <= 0:
            raise ValueError("Snapshot max daily usage must be positive")

    @property
    def limits(self) -> TierLimits:
        """Extract tier limits from snapshot."""
        return TierLimits(
            max_seconds_per_request=self.max_seconds_per_request,
            max_usage_per_day=self.max_usage_per_day,
        )
