"""PostgreSQL implementations of subscription and plan repositories."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.plan import Plan
from app.drivers.models.plan import PlanModel
from app.ports.repository import (
    PlanRepository,
)


class PostgresPlanRepository(PlanRepository):
    """PostgreSQL implementation of PlanRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> Sequence[Plan]:
        stmt = (
            select(PlanModel)
            .where(PlanModel.is_active.is_(True), PlanModel.is_deleted.is_(False))
            .order_by(PlanModel.actual_price.asc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model.to_domain() for model in models]

    async def list_all(
        self, include_deleted: bool = False, is_active: bool | None = None
    ) -> Sequence[Plan]:
        stmt = select(PlanModel)
        if not include_deleted:
            stmt = stmt.where(PlanModel.is_deleted.is_(False))
        if is_active is not None:
            stmt = stmt.where(PlanModel.is_active == is_active)
        stmt = stmt.order_by(PlanModel.actual_price.asc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model.to_domain() for model in models]

    async def get_by_code(self, code: str) -> Plan | None:
        stmt = select(PlanModel).where(PlanModel.code == code, PlanModel.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def get_by_id(self, plan_id: UUID) -> Plan | None:
        stmt = select(PlanModel).where(PlanModel.id == plan_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, plan: Plan) -> Plan:
        model = PlanModel.from_domain(plan)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged.to_domain()
