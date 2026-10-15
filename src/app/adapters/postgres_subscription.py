"""PostgreSQL implementations of subscription and plan repositories."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, or_, select
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


class PostgresSubscriptionRepository(SubscriptionRepository):
    """PostgreSQL implementation of SubscriptionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_user_id(self, user_id: str) -> Subscription | None:
        now = datetime.now(UTC)

        stmt = (
            select(SubscriptionModel)
            .where(
                SubscriptionModel.user_id == user_id,
                or_(
                    SubscriptionModel.status.in_(
                        [
                            SubscriptionStatus.ACTIVE.value,
                            SubscriptionStatus.TRIALING.value,
                        ]
                    ),
                    (SubscriptionModel.status == SubscriptionStatus.CANCELLED.value)
                    & (SubscriptionModel.current_period_end < now),
                ),
            )
            .order_by(
                case(
                    (
                        SubscriptionModel.status.in_(
                            [
                                SubscriptionStatus.ACTIVE.value,
                                SubscriptionStatus.TRIALING.value,
                            ]
                        ),
                        0,
                    ),
                    else_=1,
                ),
                SubscriptionModel.current_period_end.desc(),
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

    async def list_events(
        self,
        status: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[dict[str, Any]], int]:
        stmt = select(WebhookEventModel)
        count_stmt = select(func.count(WebhookEventModel.id))

        if status:
            stmt = stmt.where(WebhookEventModel.status == status)
            count_stmt = count_stmt.where(WebhookEventModel.status == status)
        if event_type:
            stmt = stmt.where(WebhookEventModel.event_type == event_type)
            count_stmt = count_stmt.where(WebhookEventModel.event_type == event_type)

        total_count = (await self._session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(WebhookEventModel.processed_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [
            {
                "id": str(m.id),
                "event_id": m.event_id,
                "event_type": m.event_type,
                "status": m.status,
                "payload": m.payload,
                "created_at": m.processed_at.isoformat() if m.processed_at else None,
            }
            for m in models
        ], total_count

    async def get_event_by_id(self, event_id: str) -> dict[str, Any] | None:
        stmt = select(WebhookEventModel).where(WebhookEventModel.event_id == event_id).limit(1)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None
        return {
            "id": str(m.id),
            "event_id": m.event_id,
            "event_type": m.event_type,
            "status": m.status,
            "payload": m.payload,
            "created_at": m.processed_at.isoformat() if m.processed_at else None,
        }

    async def get_status_counts(self) -> dict[str, int]:
        stmt = select(WebhookEventModel.status, func.count(WebhookEventModel.id)).group_by(
            WebhookEventModel.status
        )
        result = await self._session.execute(stmt)
        return {str(status): int(count) for status, count in result.all()}
