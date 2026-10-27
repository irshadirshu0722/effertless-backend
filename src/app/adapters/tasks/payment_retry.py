import asyncio
import logging
from uuid import UUID

from app.adapters.repositories.postgres_payment_retry_repository import (
    PostgresPaymentRetryRepository,
)
from app.adapters.repositories.postgres_subscription_repo import (
    PostgresSubscriptionRepository,
)
from app.adapters.services.payment_gateway.cashfree import CashfreeSubscriptionAdapter
from app.application.use_case.subscription.process_payment_retry import (
    ProcessPaymentRetryUseCase,
)
from app.drivers.celery_app.celery import celery_app
from app.drivers.config.database import create_session_factory

logger = logging.getLogger(__name__)


async def _process_payment_retry(retry_id: str) -> None:
    async with create_session_factory() as session:
        payment_retry_repo = PostgresPaymentRetryRepository(session)
        subscription_repo = PostgresSubscriptionRepository(session)
        payment_gateway = CashfreeSubscriptionAdapter()

        use_case = ProcessPaymentRetryUseCase(
            payment_retry_repo=payment_retry_repo,
            subscription_repo=subscription_repo,
            payment_gateway=payment_gateway,
        )

        await use_case.execute(UUID(retry_id))
        await session.commit()


@celery_app.task(
    bind=True,
    name="app.adapters.tasks.payment_retry.process_payment_retry",
    max_retries=3,
)
def process_payment_retry(self, retry_id: str) -> None:
    try:
        asyncio.run(_process_payment_retry(retry_id))
    except Exception as exc:
        logger.exception(
            "Payment retry task failed for retry_id=%s",
            retry_id,
        )
        raise self.retry(exc=exc, countdown=60) from exc
