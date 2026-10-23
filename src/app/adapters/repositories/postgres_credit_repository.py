"""PostgreSQL repository for user credit balances."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.credit import Credit
from app.drivers.models.credit import CreditModel
from app.ports.repository.credit import CreditRepository


class PostgresCreditRepository(CreditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, credit: Credit) -> Credit:
        model = await self._session.get(CreditModel, credit.id)

        if model is None:
            model = CreditModel.from_domain(credit)
            self._session.add(model)
        else:
            self._copy_to_model(model, credit)

        await self._session.flush()
        await self._session.refresh(model)
        return model.to_domain()

    async def update(self, credit: Credit) -> Credit:
        model = await self._session.get(CreditModel, credit.id)

        if model is None:
            raise ValueError(f"Credit with id {credit.id} not found")

        self._copy_to_model(model, credit)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_domain()

    async def get_by_id(self, credit_id) -> Credit | None:
        model = await self._session.get(CreditModel, credit_id)
        return model.to_domain() if model is not None else None

    async def get_by_user_id(self, user_id: str) -> Credit | None:
        statement = select(CreditModel).where(CreditModel.user_id == user_id)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return model.to_domain() if model is not None else None

    @staticmethod
    def _copy_to_model(model: CreditModel, credit: Credit) -> None:
        model.user_id = credit.user_id
        model.subscription_seconds = credit.subscription_seconds
        model.top_up_seconds = credit.top_up_seconds
