from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.repositories.postgres_plan_repo import PostgresPlanRepository
from app.core.config import settings
from app.core.logging import logging
from app.domain.entities.plan import BillingPeriod, Plan
from app.drivers.config.database import create_engine, create_session_factory

bootstrap_logger = logging.getLogger("app.bootstrap")


async def create_or_update_trail_plan() -> None:
    bootstrap_logger.info("Starting trial plan bootstrap")

    engine = create_engine()
    session_factory: async_sessionmaker[AsyncSession] = create_session_factory(engine)

    max_seconds_per_request = settings.free_tier_max_seconds
    max_requests_per_day = settings.free_tier_max_requests_per_day

    try:
        async with session_factory() as session, session.begin():
            plan_repo = PostgresPlanRepository(session)
            trial_plan = await plan_repo.get_by_code(code="trail")
            if trial_plan is None:
                bootstrap_logger.info("Trial plan not found; creating plan with code='trail'")

                new_plan = Plan(
                    actual_price=Decimal(2),
                    billing_period=BillingPeriod.YEARLY,
                    code="trail",
                    currency="INR",
                    is_active=True,
                    max_seconds_per_request=max_seconds_per_request,
                    max_usage_per_day=max_requests_per_day,
                    offer_price=Decimal(1),
                    name="trail",
                )

                await plan_repo.save(plan=new_plan)

                bootstrap_logger.info("Trial plan created successfully: code='trail'")
            else:
                bootstrap_logger.info("Trial plan found; updating usage limits: code='trail'")

                trial_plan.max_seconds_per_request = max_seconds_per_request
                trial_plan.max_usage_per_day = max_requests_per_day

                await plan_repo.update(trial_plan)

                bootstrap_logger.info("Trial plan updated successfully: code='trail'")

    except Exception:
        bootstrap_logger.exception("Trial plan bootstrap failed: code='trail'")
        raise

    finally:
        await engine.dispose()

    bootstrap_logger.info("Trial plan bootstrap completed")
