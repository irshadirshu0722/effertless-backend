"""PostgreSQL repository for the credit transaction ledger."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.credit_transaction import CreditTransaction
from app.drivers.models.credit_transaction import CreditTransactionModel
from app.ports.repository import CreditTransactionRepository


class PostgresCreditTransactionRepository(CreditTransactionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        transaction: CreditTransaction,
    ) -> CreditTransaction:
        """Append a new immutable ledger entry."""
        model = CreditTransactionModel.from_domain(transaction)
        self._session.add(model)

        await self._session.flush()
        await self._session.refresh(model)

        return model.to_domain()

    async def get_by_id(
        self,
        transaction_id: UUID,
    ) -> CreditTransaction | None:
        model = await self._session.get(
            CreditTransactionModel,
            transaction_id,
        )
        return model.to_domain() if model is not None else None

    async def list_by_user_id(
        self,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreditTransaction]:
        """List a user's transactions, newest first."""
        self._validate_pagination(limit, offset)

        statement = (
            select(CreditTransactionModel)
            .where(CreditTransactionModel.user_id == user_id)
            .order_by(
                CreditTransactionModel.created_at.desc(),
                CreditTransactionModel.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)

        return [model.to_domain() for model in result.scalars().all()]

    async def list_by_credit_id(
        self,
        credit_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreditTransaction]:
        """List ledger entries for a credit balance."""
        self._validate_pagination(limit, offset)

        statement = (
            select(CreditTransactionModel)
            .where(CreditTransactionModel.credit_id == credit_id)
            .order_by(
                CreditTransactionModel.created_at.desc(),
                CreditTransactionModel.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)

        return [model.to_domain() for model in result.scalars().all()]

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")

        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer")
