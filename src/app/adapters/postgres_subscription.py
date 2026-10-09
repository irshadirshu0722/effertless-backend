"""PostgreSQL implementations of subscription and plan repositories."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.plan import Plan
from app.domain.entities.subscription import Subscription, SubscriptionStatus
from app.drivers.models.plan import PlanModel
from app.drivers.models.subscription import SubscriptionModel
from app.drivers.models.webhook_event import WebhookEventModel
from app.ports.subscription import (
    PlanRepository,
    SubscriptionRepository,
    WebhookEventRepository,
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


class PostgresSubscriptionRepository(SubscriptionRepository):
    """PostgreSQL implementation of SubscriptionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_user_id(self, user_id: str) -> Subscription | None:
        stmt = (
            select(SubscriptionModel)
            .where(
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.status.in_(
                    [SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value]
                ),
            )
            .order_by(SubscriptionModel.current_period_end.desc())
            .limit(1)
        )
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

    async def save(self, subscription: Subscription) -> Subscription:
        model = SubscriptionModel.from_domain(subscription)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged.to_domain()


class PostgresWebhookEventRepository(WebhookEventRepository):
    """PostgreSQL implementation of WebhookEventRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_been_processed(self, event_id: str) -> bool:
        stmt = select(WebhookEventModel.id).where(WebhookEventModel.event_id == event_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def record_event(
        self,
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        status: str,
    ) -> None:
        event = WebhookEventModel(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            status=status,
        )
        self._session.add(event)
        await self._session.flush()
