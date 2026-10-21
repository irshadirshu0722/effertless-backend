from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_case.subscription import InitiateCheckoutUseCase


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
    return SimpleNamespace(
        id="plan-123",
        code="pro",
        name="Pro",
        is_active=True,
        is_deleted=False,
        max_seconds_per_request=120,
        max_usage_per_day=100,
        offer_price=Decimal("20.00"),
        currency="PLN",
        billing_period="monthly",
    )


@pytest.fixture
def user():
    return SimpleNamespace(
        user_id="user-123",
        email="user@example.com",
    )
