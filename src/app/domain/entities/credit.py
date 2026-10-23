"""User credit balance entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def _validate_seconds(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


@dataclass(slots=True)
class Credit:
    """Stores subscription and top-up balances for one user."""

    user_id: str
    subscription_seconds: int = 0
    top_up_seconds: int = 0

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.user_id = self.user_id.strip()

        if not self.user_id:
            raise ValueError("user_id cannot be empty")

        _validate_seconds(self.subscription_seconds, "subscription_seconds")
        _validate_seconds(self.top_up_seconds, "top_up_seconds")

        for field_name in ("created_at", "updated_at"):
            value = getattr(self, field_name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")

    @property
    def total_seconds(self) -> int:
        """Return the total available balance."""
        return self.subscription_seconds + self.top_up_seconds

    def grant_subscription(self, seconds: int) -> None:
        """Grant subscription seconds."""
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
            raise ValueError("seconds must be a positive integer")

        self.subscription_seconds += seconds
        self.updated_at = datetime.now(UTC)

    def grant_top_up(self, seconds: int) -> None:
        """Grant purchased top-up seconds."""
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
            raise ValueError("seconds must be a positive integer")

        self.top_up_seconds += seconds
        self.updated_at = datetime.now(UTC)

    def consume(self, seconds: int) -> tuple[int, int]:
        """Consume subscription credits first, then top-up credits.

        Returns:
            A tuple of (subscription_seconds_consumed, top_up_seconds_consumed).
        """
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
            raise ValueError("seconds must be a positive integer")

        if seconds > self.total_seconds:
            raise ValueError("insufficient credits")

        subscription_used = min(self.subscription_seconds, seconds)
        top_up_used = seconds - subscription_used

        self.subscription_seconds -= subscription_used
        self.top_up_seconds -= top_up_used
        self.updated_at = datetime.now(UTC)

        return subscription_used, top_up_used
