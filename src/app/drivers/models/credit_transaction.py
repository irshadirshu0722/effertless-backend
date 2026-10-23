"""Credit transaction ledger SQLAlchemy model."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.credit_transaction import (
    CreditTransaction,
    CreditTransactionType,
)
from app.drivers.models.base import Base


class CreditTransactionModel(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    credit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("credits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    transaction_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    subscription_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    top_up_delta: Mapped[int] = mapped_column(Integer, nullable=False)

    subscription_balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    top_up_balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    reference_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    def to_domain(self) -> CreditTransaction:
        return CreditTransaction(
            id=self.id,
            credit_id=self.credit_id,
            user_id=self.user_id,
            transaction_type=CreditTransactionType(self.transaction_type),
            subscription_delta=self.subscription_delta,
            top_up_delta=self.top_up_delta,
            subscription_balance_after=self.subscription_balance_after,
            top_up_balance_after=self.top_up_balance_after,
            reference_id=self.reference_id,
            description=self.description,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(
        cls,
        transaction: CreditTransaction,
    ) -> "CreditTransactionModel":
        return cls(
            id=transaction.id,
            credit_id=transaction.credit_id,
            user_id=transaction.user_id,
            transaction_type=transaction.transaction_type.value,
            subscription_delta=transaction.subscription_delta,
            top_up_delta=transaction.top_up_delta,
            subscription_balance_after=(transaction.subscription_balance_after),
            top_up_balance_after=transaction.top_up_balance_after,
            reference_id=transaction.reference_id,
            description=transaction.description,
            created_at=transaction.created_at,
        )
