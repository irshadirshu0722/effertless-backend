"""SQLAlchemy model for user subscriptions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.subscription import (
    ReplacementStrategy,
    Subscription,
    SubscriptionOperationType,
    SubscriptionStatus,
)
from app.drivers.models.base import Base


class SubscriptionModel(Base):
    """Database model for subscriptions."""

    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    user_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="cashfree",
    )

    external_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    external_customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    operation_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SubscriptionOperationType.NEW.value,
    )

    related_subscription_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    snapshot_plan_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    snapshot_max_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    snapshot_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    snapshot_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    has_trial: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    trial_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    trial_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    replacement_strategy: Mapped[str] = mapped_column(
        String(20),
        nullable=True,
        default=ReplacementStrategy.IMMEDIATE,
    )

    def to_domain(self) -> Subscription:
        """Convert a database model into a domain entity."""
        return Subscription(
            id=self.id,
            user_id=self.user_id,
            plan_id=self.plan_id,
            status=SubscriptionStatus(self.status),
            provider=self.provider,
            external_subscription_id=self.external_subscription_id,
            external_customer_id=self.external_customer_id,
            current_period_start=self.current_period_start,
            current_period_end=self.current_period_end,
            cancelled_at=self.cancelled_at,
            is_active=self.is_active,
            related_subscription_id=self.related_subscription_id,
            operation_type=SubscriptionOperationType(self.operation_type),
            snapshot_plan_name=self.snapshot_plan_name,
            snapshot_max_seconds=self.snapshot_max_seconds,
            snapshot_price=self.snapshot_price,
            snapshot_currency=self.snapshot_currency,
            created_at=self.created_at,
            updated_at=self.updated_at,
            has_trial=self.has_trial,
            trial_start=self.trial_start,
            trial_end=self.trial_end,
            replacement_strategy=self.replacement_strategy,
        )

    @classmethod
    def from_domain(cls, sub: Subscription) -> SubscriptionModel:
        """Construct a database model from a domain entity."""
        snapshot_fields = {
            "snapshot_plan_name": sub.snapshot_plan_name,
            "snapshot_max_seconds": sub.snapshot_max_seconds,
            "snapshot_price": sub.snapshot_price,
            "snapshot_currency": sub.snapshot_currency,
        }

        missing_fields = [name for name, value in snapshot_fields.items() if value is None]

        if missing_fields:
            raise ValueError(
                "Cannot persist a subscription without a complete "
                f"plan snapshot. Missing: {', '.join(missing_fields)}"
            )

        return cls(
            id=sub.id,
            user_id=sub.user_id,
            plan_id=sub.plan_id,
            status=sub.status.value,
            provider=sub.provider,
            external_subscription_id=sub.external_subscription_id,
            external_customer_id=sub.external_customer_id,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            cancelled_at=sub.cancelled_at,
            is_active=sub.is_active,
            related_subscription_id=sub.related_subscription_id,
            operation_type=sub.operation_type.value,
            snapshot_plan_name=sub.snapshot_plan_name,
            snapshot_max_seconds=sub.snapshot_max_seconds,
            snapshot_price=sub.snapshot_price,
            snapshot_currency=sub.snapshot_currency,
            has_trial=sub.has_trial,
            trial_start=sub.trial_start,
            trial_end=sub.trial_end,
            replacement_strategy=sub.replacement_strategy,
        )
