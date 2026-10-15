"""Unit tests for PlanAdmin payment-provider sync hooks."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.admin.views import PlanAdmin
from app.domain.entities.plan import Plan
from app.drivers.models.plan import PlanModel


class FakePaymentGateway:
    def __init__(self) -> None:
        self.created_plans: list[Plan] = []
        self.deleted_plan_codes: list[str] = []

    async def create_plan(self, plan: Plan) -> bool:
        self.created_plans.append(plan)
        return True

    async def delete_plan(self, plan_code: str) -> bool:
        self.deleted_plan_codes.append(plan_code)
        return True


def fake_request(gateway: FakePaymentGateway):
    app = SimpleNamespace(state=SimpleNamespace(payment_gateway=gateway))
    return SimpleNamespace(app=app)


def test_plan_admin_disables_editing() -> None:
    assert PlanAdmin.can_create is True
    assert PlanAdmin.can_edit is False
    assert PlanAdmin.can_delete is True


@pytest.mark.asyncio
async def test_plan_admin_create_syncs_cashfree_plan() -> None:
    gateway = FakePaymentGateway()
    admin = PlanAdmin()
    data = {
        "code": "lite_monthly",
        "name": "Lite",
        "billing_period": "monthly",
        "actual_price": Decimal("499.00"),
        "offer_price": Decimal("299.00"),
        "currency": "INR",
        "max_seconds_per_request": 30,
        "max_usage_per_day": 50,
        "is_active": True,
        "is_deleted": False,
    }

    await admin.on_model_change(
        data, model=PlanModel(), is_created=True, request=fake_request(gateway)
    )

    assert [plan.code for plan in gateway.created_plans] == ["lite_monthly"]
    assert gateway.created_plans[0].offer_price == Decimal("299.00")


@pytest.mark.asyncio
async def test_plan_admin_delete_syncs_cashfree_plan() -> None:
    gateway = FakePaymentGateway()
    admin = PlanAdmin()
    model = PlanModel(
        code="lite_monthly",
        name="Lite",
        billing_period="monthly",
        actual_price=Decimal("499.00"),
        offer_price=Decimal("299.00"),
        max_seconds_per_request=30,
        max_usage_per_day=50,
    )

    await admin.on_model_delete(model, request=fake_request(gateway))

    assert gateway.deleted_plan_codes == ["lite_monthly"]
