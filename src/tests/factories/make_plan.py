"""Plan test factory."""

from decimal import Decimal

from app.domain.entities.plan import PLAN_NAMES, Plan, PlanCode


def make_plan_data(**overrides) -> Plan:
    code = overrides.get("code", PlanCode.BASIC)

    data = {
        "code": code,
        "name": PLAN_NAMES[code],
        "monthly_seconds": 3600,
        "actual_price": Decimal("299.00"),
        "offer_price": Decimal("200.00"),
        "currency": "INR",
        "is_active": True,
        "is_deleted": False,
    }
    data.update(overrides)

    return Plan(**data)
