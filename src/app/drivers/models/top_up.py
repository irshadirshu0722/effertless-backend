"""Top-up SQLAlchemy model."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.top_up import TopUp, TopUpStatus
from app.drivers.models.base import Base


class TopUpModel(Base):
    __tablename__ = "top_ups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    seconds: Mapped[int] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    external_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_domain(self) -> TopUp:
        return TopUp(
            id=self.id,
            user_id=self.user_id,
            seconds=self.seconds,
            amount=self.amount,
            currency=self.currency,
            status=TopUpStatus(self.status),
            provider=self.provider,
            external_payment_id=self.external_payment_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            completed_at=self.completed_at,
        )

    @classmethod
    def from_domain(cls, top_up: TopUp) -> "TopUpModel":
        return cls(
            id=top_up.id,
            user_id=top_up.user_id,
            seconds=top_up.seconds,
            amount=top_up.amount,
            currency=top_up.currency,
            status=top_up.status.value,
            provider=top_up.provider,
            external_payment_id=top_up.external_payment_id,
            created_at=top_up.created_at,
            updated_at=top_up.updated_at,
            completed_at=top_up.completed_at,
        )
