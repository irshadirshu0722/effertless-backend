from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_case.subscription import InitiateCheckoutUseCase
from tests.factories.make_plan import make_plan_data


@pytest.fixture
def initiate_checkout_service(
    subscription_repo,
    payment_gateway,
    plan_repo,
):
    return InitiateCheckoutUseCase(
        payment_gateway=payment_gateway,
        plan_repo=plan_repo,
        subscription_repo=subscription_repo,
    )


@pytest.fixture
def active_plan():
    now = datetime.now(UTC)

    return make_plan_data(
        id="plan-123",
        code="PRO",
        name="Pro",
        monthly_seconds=3600,
        actual_price=Decimal("20.00"),
        offer_price=Decimal("20.00"),
        currency="PLN",
        is_active=True,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def user():
    return SimpleNamespace(
        user_id="user-123",
        email="user@example.com",
    )
