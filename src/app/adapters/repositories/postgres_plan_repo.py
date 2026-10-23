"""PostgreSQL repository for subscription plans."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.plan import Plan, PlanCode
from app.drivers.models.plan import PlanModel


class PostgresPlanRepository:
    """Persist and retrieve subscription plans using PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, plan: Plan) -> Plan:
        """Insert a plan or persist changes to an existing plan."""
        model = await self._session.get(PlanModel, plan.id)

        if model is None:
            model = PlanModel.from_domain(plan)
            self._session.add(model)
        else:
            self._update_model(model, plan)

        await self._session.flush()
        await self._session.refresh(model)

        return model.to_domain()

    async def update(self, plan: Plan) -> Plan:
        """Update an existing plan; raise if it does not exist."""
        model = await self._session.get(PlanModel, plan.id)

        if model is None:
            raise ValueError(f"Plan with id {plan.id} not found")

        self._update_model(model, plan)

        await self._session.flush()
        await self._session.refresh(model)

        return model.to_domain()

    async def get_by_id(self, plan_id: UUID) -> Plan | None:
        """Retrieve a non-deleted plan by its ID."""
        statement = select(PlanModel).where(
            PlanModel.id == plan_id,
            PlanModel.is_deleted.is_(False),
        )

        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        return model.to_domain() if model is not None else None

    async def get_by_code(self, code: PlanCode | str) -> Plan | None:
        """Retrieve a non-deleted plan by its fixed code."""
        code_value = (code.value if isinstance(code, PlanCode) else code).strip().upper()

        statement = select(PlanModel).where(
            PlanModel.code == code_value,
            PlanModel.is_deleted.is_(False),
        )

        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        return model.to_domain() if model is not None else None

    async def get_by_id_including_deleted(
        self,
        plan_id: UUID,
    ) -> Plan | None:
        """Retrieve a plan by ID, including soft-deleted plans."""
        model = await self._session.get(PlanModel, plan_id)

        return model.to_domain() if model is not None else None

    async def list_active(self) -> list[Plan]:
        """List active, non-deleted plans ordered by actual price."""
        statement = (
            select(PlanModel)
            .where(
                PlanModel.is_active.is_(True),
                PlanModel.is_deleted.is_(False),
            )
            .order_by(PlanModel.actual_price.asc(), PlanModel.code.asc())
        )

        result = await self._session.execute(statement)
        return [model.to_domain() for model in result.scalars().all()]

    async def list_all(
        self,
        *,
        include_deleted: bool = False,
        is_active: bool | None = None,
    ) -> list[Plan]:
        """List plans with optional deletion and active-status filters."""
        statement = select(PlanModel)

        if not include_deleted:
            statement = statement.where(PlanModel.is_deleted.is_(False))

        if is_active is not None:
            statement = statement.where(PlanModel.is_active.is_(is_active))

        statement = statement.order_by(
            PlanModel.actual_price.asc(),
            PlanModel.code.asc(),
        )

        result = await self._session.execute(statement)
        return [model.to_domain() for model in result.scalars().all()]

    @staticmethod
    def _update_model(model: PlanModel, plan: Plan) -> None:
        """Copy domain values to an existing ORM model."""
        model.code = plan.code.value
        model.name = plan.name
        model.monthly_seconds = plan.monthly_seconds
        model.actual_price = plan.actual_price
        model.offer_price = plan.offer_price
        model.currency = plan.currency
        model.is_active = plan.is_active
        model.is_deleted = plan.is_deleted
