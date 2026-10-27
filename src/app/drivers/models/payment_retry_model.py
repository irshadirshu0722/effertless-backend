from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

# Replace with the Base imported by your existing SubscriptionModel.
from app.drivers.models.base import Base


class PaymentRetryModel(Base):
    __tablename__ = "payment_retries"

    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "billing_period_start",
            name="uq_payment_retries_subscription_period",
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="ck_payment_retries_retry_count_nonnegative",
        ),
        CheckConstraint(
            "max_retries >= 1",
            name="ck_payment_retries_max_retries_positive",
        ),
        Index(
            "ix_payment_retries_due",
            "status",
            "next_retry_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    subscription_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )

    billing_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    retry_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    max_retries: Mapped[int] = mapped_column(
        nullable=False,
        default=3,
    )

    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="SCHEDULED",
    )

    last_payment_attempt_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=None,  # Replace with your project's timestamp convention.
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=None,  # Replace with your project's timestamp convention.
    )
