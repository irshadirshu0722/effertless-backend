"""SQLAlchemy model for user subscriptions."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.subscription import Subscription, SubscriptionStatus
from app.domain.value_objects.plan_snapshot import PlanSnapshot
from app.drivers.models.base import Base


class SubscriptionModel(Base):
    """Database model for subscriptions table."""

    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="cashfree")
    external_subscription_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    external_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Frozen snapshot fields
    snapshot_plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    snapshot_max_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_max_usage_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    snapshot_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def to_domain(self) -> Subscription:
        """Convert ORM model to immutable domain entity."""
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
            snapshot=PlanSnapshot(
                plan_name=self.snapshot_plan_name,
                max_seconds_per_request=self.snapshot_max_seconds,
                max_usage_per_day=self.snapshot_max_usage_per_day,
                price=self.snapshot_price,
                currency=self.snapshot_currency,
            ),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, sub: Subscription) -> "SubscriptionModel":
        """Construct ORM model from domain entity."""
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
            snapshot_plan_name=sub.snapshot.plan_name,
            snapshot_max_seconds=sub.snapshot.max_seconds_per_request,
            snapshot_max_usage_per_day=sub.snapshot.max_usage_per_day,
            snapshot_price=sub.snapshot.price,
            snapshot_currency=sub.snapshot.currency,
        )
