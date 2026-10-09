"""Use case for listing active subscription plans."""

from collections.abc import Sequence

from app.domain.entities.plan import Plan
from app.ports.subscription import PlanRepository


class ListPlansUseCase:
    """Retrieves all non-deleted, active subscription plans."""

    def __init__(self, plan_repo: PlanRepository) -> None:
        self._plan_repo = plan_repo

    async def execute(self) -> Sequence[Plan]:
        return await self._plan_repo.list_active()
