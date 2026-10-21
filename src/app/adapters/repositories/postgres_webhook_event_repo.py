"""PostgreSQL implementations of subscription and plan repositories."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.drivers.models.webhook_event import WebhookEventModel
from app.ports.repository import (
    WebhookEventRepository,
)


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
