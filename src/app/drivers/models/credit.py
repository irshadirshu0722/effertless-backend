"""Credit balance SQLAlchemy model."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.credit import Credit
from app.drivers.models.base import Base


class CreditModel(Base):
    __tablename__ = "credits"
    __table_args__ = (UniqueConstraint("user_id", name="uq_credits_user_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_up_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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

    def to_domain(self) -> Credit:
        return Credit(
            id=self.id,
            user_id=self.user_id,
            subscription_seconds=self.subscription_seconds,
            top_up_seconds=self.top_up_seconds,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, credit: Credit) -> "CreditModel":
        return cls(
            id=credit.id,
            user_id=credit.user_id,
            subscription_seconds=credit.subscription_seconds,
            top_up_seconds=credit.top_up_seconds,
            created_at=credit.created_at,
            updated_at=credit.updated_at,
        )
