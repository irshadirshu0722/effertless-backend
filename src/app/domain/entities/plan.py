"""Plan domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class PlanCode(StrEnum):
    """Supported subscription plans."""

    BASIC = "BASIC"
    STANDARD = "STANDARD"
    PRO = "PRO"


PLAN_NAMES = {
    PlanCode.BASIC: "Basic",
    PlanCode.STANDARD: "Standard",
    PlanCode.PRO: "Pro",
}


@dataclass(slots=True)
class Plan:
    """Fixed monthly subscription plan."""

    code: PlanCode | str
    name: str
    monthly_seconds: int
    actual_price: Decimal
    offer_price: Decimal | None = None

    id: UUID = field(default_factory=uuid4)
    currency: str = "INR"
    is_active: bool = True
    is_deleted: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self._validate_code()
        self._validate_name()
        self._validate_monthly_seconds()
        self._validate_prices()
        self._validate_currency()
        self._validate_timestamps()

    def _validate_code(self) -> None:
        try:
            self.code = PlanCode(str(self.code).strip().upper())
        except ValueError as exc:
            raise ValueError("code must be BASIC, STANDARD, or PRO") from exc

    def _validate_name(self) -> None:
        self.name = self.name.strip()

        if not self.name:
            raise ValueError("name cannot be empty")

        expected_name = PLAN_NAMES[self.code]

        if self.name != expected_name:
            raise ValueError(f"name for {self.code.value} must be {expected_name!r}")

    def _validate_monthly_seconds(self) -> None:
        if (
            isinstance(self.monthly_seconds, bool)
            or not isinstance(self.monthly_seconds, int)
            or self.monthly_seconds <= 0
        ):
            raise ValueError("monthly_seconds must be a positive integer")

    def _validate_prices(self) -> None:
        self.actual_price = self._to_decimal(
            self.actual_price,
            "actual_price",
        )

        if self.actual_price < 0:
            raise ValueError("actual_price cannot be negative")

        if self.offer_price is not None:
            self.offer_price = self._to_decimal(
                self.offer_price,
                "offer_price",
            )

            if self.offer_price < 0:
                raise ValueError("offer_price cannot be negative")

            if self.offer_price > self.actual_price:
                raise ValueError("offer_price cannot exceed actual_price")

    @staticmethod
    def _to_decimal(
        value: Decimal | int | float | str,
        field_name: str,
    ) -> Decimal:
        if isinstance(value, bool):
            raise ValueError(f"{field_name} must be a valid price")

        try:
            price = Decimal(str(value))
        except (ValueError, TypeError, ArithmeticError) as exc:
            raise ValueError(f"{field_name} must be a valid price") from exc

        if not price.is_finite():
            raise ValueError(f"{field_name} must be finite")

        return price

    def _validate_currency(self) -> None:
        self.currency = self.currency.strip().upper()

        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isascii():
            raise ValueError("currency must be a three-letter currency code")

    def _validate_timestamps(self) -> None:
        for field_name in ("created_at", "updated_at"):
            value = getattr(self, field_name)

            if (value is not None and value.tzinfo is None) or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")

    @property
    def effective_price(self) -> Decimal:
        """Return the offer price when available."""
        if self.offer_price is not None:
            return self.offer_price

        return self.actual_price

    @property
    def is_available(self) -> bool:
        """Whether the plan can be purchased."""
        return self.is_active and not self.is_deleted
