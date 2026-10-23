"""Contract for credit transaction repository implementations."""

from typing import Protocol
from uuid import UUID

from app.domain.entities.credit_transaction import CreditTransaction


class CreditTransactionRepository(Protocol):
    """Repository contract for the immutable credit transaction ledger."""

    async def create(
        self,
        transaction: CreditTransaction,
    ) -> CreditTransaction:
        """Append a new immutable ledger entry."""
        ...

    async def get_by_id(
        self,
        transaction_id: UUID,
    ) -> CreditTransaction | None:
        """Retrieve a transaction by its ID."""
        ...

    async def list_by_user_id(
        self,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreditTransaction]:
        """List a user's transactions, newest first."""
        ...

    async def list_by_credit_id(
        self,
        credit_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreditTransaction]:
        """List transactions for a specific credit balance."""
        ...
