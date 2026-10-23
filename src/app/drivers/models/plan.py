"""Plan SQLAlchemy model."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.plan import Plan
from app.drivers.models.base import Base


class PlanModel(Base):
    """Persistence model for fixed monthly plans."""

    __tablename__ = "plans"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    monthly_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    actual_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    offer_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

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

    def to_domain(self) -> Plan:
        """Convert ORM model to domain entity."""
        return Plan(
            id=self.id,
            code=self.code,
            name=self.name,
            monthly_seconds=self.monthly_seconds,
            actual_price=self.actual_price,
            offer_price=self.offer_price,
            currency=self.currency,
            is_active=self.is_active,
            is_deleted=self.is_deleted,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, plan: Plan) -> "PlanModel":
        """Create ORM model from domain entity."""
        return cls(
            id=plan.id,
            code=plan.code.value,
            name=plan.name,
            monthly_seconds=plan.monthly_seconds,
            actual_price=plan.actual_price,
            offer_price=plan.offer_price,
            currency=plan.currency,
            is_active=plan.is_active,
            is_deleted=plan.is_deleted,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
