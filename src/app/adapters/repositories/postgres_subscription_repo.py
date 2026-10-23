"""PostgreSQL implementations of subscription and plan repositories."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.subscription import Subscription, SubscriptionStatus
from app.drivers.models.subscription import SubscriptionModel
from app.ports.repository import SubscriptionRepository


class PostgresSubscriptionRepository(SubscriptionRepository):
    """PostgreSQL implementation of SubscriptionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_user_id(self, user_id: str) -> Subscription | None:
        stmt = (
            select(SubscriptionModel)
            .where(
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.is_active.is_(True),
            )
            .limit(1)
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return model.to_domain() if model else None

    async def get_latest_by_user_id(self, user_id: str) -> Subscription | None:
        stmt = (
            select(SubscriptionModel)
            .where(SubscriptionModel.user_id == user_id)
            .order_by(SubscriptionModel.current_period_end.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def get_by_id(self, subscription_id: UUID) -> Subscription | None:
        stmt = select(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def get_by_external_id(self, external_id: str) -> Subscription | None:
        stmt = (
            select(SubscriptionModel)
            .where(SubscriptionModel.external_subscription_id == external_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_all(
        self,
        user_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Subscription], int]:
        stmt = select(SubscriptionModel)
        count_stmt = select(func.count(SubscriptionModel.id))

        if user_id:
            stmt = stmt.where(SubscriptionModel.user_id == user_id)
            count_stmt = count_stmt.where(SubscriptionModel.user_id == user_id)
        if status:
            stmt = stmt.where(SubscriptionModel.status == status)
            count_stmt = count_stmt.where(SubscriptionModel.status == status)

        total_count = (await self._session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(SubscriptionModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model.to_domain() for model in models], total_count

    async def get_status_counts(self) -> dict[str, int]:
        stmt = select(SubscriptionModel.status, func.count(SubscriptionModel.id)).group_by(
            SubscriptionModel.status
        )
        result = await self._session.execute(stmt)
        return {str(status): int(count) for status, count in result.all()}

    async def save(self, subscription: Subscription) -> Subscription:
        model = SubscriptionModel.from_domain(subscription)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged.to_domain()

    async def get(self, **filters: Any) -> Subscription | None:
        """Get one subscription matching the supplied field filters."""
        stmt = select(SubscriptionModel)

        for field, value in filters.items():
            column = getattr(SubscriptionModel, field, None)

            if column is None:
                raise ValueError(f"Invalid subscription filter field: {field}")

            stmt = stmt.where(column.is_(None) if value is None else column == value)

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return model.to_domain() if model else None

    async def has_user_used_trial(self, user_id: str) -> bool:
        statement = select(
            exists().where(
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.has_trial.is_(True),
                SubscriptionModel.status != SubscriptionStatus.PENDING,
            )
        )

        result = await self.session.execute(statement)
        return result.scalar_one()
