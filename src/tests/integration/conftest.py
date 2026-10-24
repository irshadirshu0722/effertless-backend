import pytest
import pytest_asyncio

from app.adapters.repositories import (
    PostgresCreditRepository,
    PostgresCreditTransactionRepository,
    PostgresPlanRepository,
    PostgresSubscriptionRepository,
    PostgresTopUpRepository,
    PostgresWebhookEventRepository,
)
from app.domain.entities.plan import PLAN_NAMES, PlanCode
from tests.factories import make_plan_data


@pytest.fixture
def subscription_repo(db_session):
    return PostgresSubscriptionRepository(session=db_session)


@pytest.fixture
def plan_repo(db_session):
    return PostgresPlanRepository(session=db_session)


@pytest.fixture
def webhook_event_repo(db_session):
    return PostgresWebhookEventRepository(session=db_session)


@pytest.fixture
def credit_repo(db_session):
    return PostgresCreditRepository(session=db_session)


@pytest.fixture
def top_up_repo(db_session):
    return PostgresTopUpRepository(session=db_session)


@pytest.fixture
def credit_transaction_repo(db_session):
    return PostgresCreditTransactionRepository(session=db_session)


@pytest_asyncio.fixture
async def created_plan(plan_repo):
    plan = make_plan_data()
    return await plan_repo.save(plan)


@pytest_asyncio.fixture
async def create_all_plan(plan_repo):
    plans = {}

    for code in (
        PlanCode.TRAIL,
        PlanCode.BASIC,
        PlanCode.STANDARD,
        PlanCode.PRO,
    ):
        plan = make_plan_data(
            code=code,
            name=PLAN_NAMES[code],
        )
        plans[code] = await plan_repo.save(plan)

    return plans
