import pytest
import pytest_asyncio

from app.adapters.repositories import (
    PostgresPlanRepository,
    PostgresSubscriptionRepository,
    PostgresWebhookEventRepository,
)
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


@pytest_asyncio.fixture
async def created_plan(plan_repo):
    plan = make_plan_data()
    return await plan_repo.save(plan)
