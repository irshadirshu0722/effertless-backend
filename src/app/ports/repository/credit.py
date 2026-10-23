"""Contract for credit repository implementations."""

from typing import Protocol
from uuid import UUID

from app.domain.entities.credit import Credit


class CreditRepository(Protocol):
    """Repository contract for managing user credit balances."""

    async def save(self, credit: Credit) -> Credit:
        """Create or persist a credit balance."""
        ...

    async def update(self, credit: Credit) -> Credit:
        """Update an existing credit balance."""
        ...

    async def get_by_id(self, credit_id: UUID) -> Credit | None:
        """Retrieve a credit balance by its ID."""
        ...

    async def get_by_user_id(self, user_id: str) -> Credit | None:
        """Retrieve a credit balance by its user ID."""
        ...
