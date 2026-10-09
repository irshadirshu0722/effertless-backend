"""Usage balance and daily quota value objects."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UsageBalance:
    """Represents a user's current daily usage consumption."""

    used_today: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used_today)

    @property
    def is_exhausted(self) -> bool:
        return self.used_today >= self.limit
