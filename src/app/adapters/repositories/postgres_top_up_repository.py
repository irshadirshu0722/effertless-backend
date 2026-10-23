"""PostgreSQL repository for top-up purchases."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.top_up import TopUp
from app.drivers.models.top_up import TopUpModel
from app.ports.repository import TopUpRepository


class PostgresTopUpRepository(TopUpRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, top_up: TopUp) -> TopUp:
        model = await self._session.get(TopUpModel, top_up.id)

        if model is None:
            model = TopUpModel.from_domain(top_up)
            self._session.add(model)
        else:
            self._copy_to_model(model, top_up)

        await self._session.flush()
        await self._session.refresh(model)
        return model.to_domain()

    async def update(self, top_up: TopUp) -> TopUp:
        model = await self._session.get(TopUpModel, top_up.id)

        if model is None:
            raise ValueError(f"Top-up with id {top_up.id} not found")

        self._copy_to_model(model, top_up)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_domain()

    async def get_by_id(self, top_up_id: UUID) -> TopUp | None:
        model = await self._session.get(TopUpModel, top_up_id)
        return model.to_domain() if model is not None else None

    async def get_by_external_payment_id(
        self,
        external_payment_id: str,
    ) -> TopUp | None:
        statement = select(TopUpModel).where(TopUpModel.external_payment_id == external_payment_id)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return model.to_domain() if model is not None else None

    async def list_by_user_id(self, user_id: str) -> list[TopUp]:
        statement = (
            select(TopUpModel)
            .where(TopUpModel.user_id == user_id)
            .order_by(TopUpModel.created_at.desc())
        )
        result = await self._session.execute(statement)
        return [model.to_domain() for model in result.scalars().all()]

    @staticmethod
    def _copy_to_model(model: TopUpModel, top_up: TopUp) -> None:
        model.user_id = top_up.user_id
        model.seconds = top_up.seconds
        model.amount = top_up.amount
        model.currency = top_up.currency
        model.status = top_up.status.value
        model.provider = top_up.provider
        model.external_payment_id = top_up.external_payment_id
        model.created_at = top_up.created_at
        model.updated_at = top_up.updated_at
        model.completed_at = top_up.completed_at
