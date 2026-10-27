from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.payment_retry import (
    PaymentRetry,
    PaymentRetryStatus,
)
from app.drivers.models.payment_retry_model import PaymentRetryModel
from app.ports.repository.payment_retry_repository import (
    PaymentRetryRepository,
)


class PostgresPaymentRetryRepository(PaymentRetryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: PaymentRetryModel) -> PaymentRetry:
        return PaymentRetry(
            id=model.id,
            subscription_id=model.subscription_id,
            billing_period_start=model.billing_period_start,
            retry_count=model.retry_count,
            max_retries=model.max_retries,
            next_retry_at=model.next_retry_at,
            status=PaymentRetryStatus(model.status),
            last_payment_attempt_id=model.last_payment_attempt_id,
            last_error=model.last_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _apply_entity(
        model: PaymentRetryModel,
        retry: PaymentRetry,
    ) -> None:
        model.subscription_id = retry.subscription_id
        model.billing_period_start = retry.billing_period_start
        model.retry_count = retry.retry_count
        model.max_retries = retry.max_retries
        model.next_retry_at = retry.next_retry_at
        model.status = retry.status.value
        model.last_payment_attempt_id = retry.last_payment_attempt_id
        model.last_error = retry.last_error
        model.updated_at = retry.updated_at

    async def save(self, retry: PaymentRetry) -> PaymentRetry:
        model = await self._session.get(PaymentRetryModel, retry.id)

        if model is None:
            model = PaymentRetryModel(
                id=retry.id,
                subscription_id=retry.subscription_id,
                billing_period_start=retry.billing_period_start,
                retry_count=retry.retry_count,
                max_retries=retry.max_retries,
                next_retry_at=retry.next_retry_at,
                status=retry.status.value,
                last_payment_attempt_id=retry.last_payment_attempt_id,
                last_error=retry.last_error,
                created_at=retry.created_at,
                updated_at=retry.updated_at,
            )
            self._session.add(model)
        else:
            self._apply_entity(model, retry)

        await self._session.flush()
        await self._session.refresh(model)

        return self._to_entity(model)

    async def get_by_id(self, retry_id: UUID) -> PaymentRetry | None:
        model = await self._session.get(PaymentRetryModel, retry_id)

        if model is None:
            return None

        return self._to_entity(model)

    async def get_by_subscription_and_period(
        self,
        subscription_id: UUID,
        billing_period_start: datetime,
    ) -> PaymentRetry | None:
        statement = select(PaymentRetryModel).where(
            PaymentRetryModel.subscription_id == subscription_id,
            PaymentRetryModel.billing_period_start == billing_period_start,
        )

        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_entity(model)

    async def list_due(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[PaymentRetry]:
        if limit < 1:
            raise ValueError("limit must be at least 1")

        statement = (
            select(PaymentRetryModel)
            .where(
                PaymentRetryModel.status == PaymentRetryStatus.SCHEDULED.value,
                PaymentRetryModel.next_retry_at.is_not(None),
                PaymentRetryModel.next_retry_at <= now,
            )
            .order_by(PaymentRetryModel.next_retry_at.asc())
            .limit(limit)
        )

        result = await self._session.execute(statement)
        return [self._to_entity(model) for model in result.scalars().all()]
