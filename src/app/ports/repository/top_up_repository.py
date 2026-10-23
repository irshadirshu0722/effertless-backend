"""Contract for top-up repository implementations."""

from typing import Protocol
from uuid import UUID

from app.domain.entities.top_up import TopUp


class TopUpRepository(Protocol):
    """Repository contract for managing top-up purchases."""

    async def save(self, top_up: TopUp) -> TopUp:
        """Create or persist a top-up purchase."""
        ...

    async def update(self, top_up: TopUp) -> TopUp:
        """Update an existing top-up purchase."""
        ...

    async def get_by_id(self, top_up_id: UUID) -> TopUp | None:
        """Retrieve a top-up purchase by its ID."""
        ...

    async def get_by_external_payment_id(
        self,
        external_payment_id: str,
    ) -> TopUp | None:
        """Retrieve a top-up purchase by its external payment ID."""
        ...

    async def list_by_user_id(self, user_id: str) -> list[TopUp]:
        """List a user's top-up purchases, newest first."""
        ...
