"""SQLAlchemy model for subscription plans."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.plan import Plan
from app.drivers.models.base import Base


class PlanModel(Base):
    """Database model for plans table."""

    __tablename__ = "plans"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_period: Mapped[str] = mapped_column(String(20), nullable=False)
    actual_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    offer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    max_seconds_per_request: Mapped[int] = mapped_column(Integer, nullable=False)
    max_usage_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def to_domain(self) -> Plan:
        """Convert ORM model to immutable domain entity."""
        return Plan(
            id=self.id,
            code=self.code,
            name=self.name,
            billing_period=self.billing_period,
            actual_price=self.actual_price,
            offer_price=self.offer_price,
            currency=self.currency,
            max_seconds_per_request=self.max_seconds_per_request,
            max_usage_per_day=self.max_usage_per_day,
            is_active=self.is_active,
            is_deleted=self.is_deleted,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, plan: Plan) -> "PlanModel":
        """Construct ORM model from domain entity."""
        return cls(
            id=plan.id,
            code=plan.code,
            name=plan.name,
            billing_period=str(plan.billing_period),
            actual_price=plan.actual_price,
            offer_price=plan.offer_price,
            currency=plan.currency,
            max_seconds_per_request=plan.max_seconds_per_request,
            max_usage_per_day=plan.max_usage_per_day,
            is_active=plan.is_active,
            is_deleted=plan.is_deleted,
        )
