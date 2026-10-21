from decimal import Decimal
from uuid import uuid4

from app.domain.entities.plan import Plan


def make_plan_data(
    *,
    code="pro",
    name="Pro",
    actual_price=Decimal("30.00"),
    offer_price=Decimal("20.00"),
    is_active=True,
    is_deleted=False,
):
    return Plan(
        id=uuid4(),
        code=code,
        name=name,
        actual_price=actual_price,
        offer_price=offer_price,
        currency="PLN",
        billing_period="monthly",
        max_seconds_per_request=120,
        max_usage_per_day=100,
        is_active=is_active,
        is_deleted=is_deleted,
    )
