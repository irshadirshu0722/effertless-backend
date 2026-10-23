"""Plan test factory."""

from decimal import Decimal

from app.domain.entities.plan import PLAN_NAMES, Plan, PlanCode


def make_plan_data(**overrides) -> Plan:
    """Build a valid Plan with optional overrides."""

    data = {
        "code": PlanCode.BASIC,
        "name": PLAN_NAMES[overrides.get("code")],
        "monthly_seconds": 3600,
        "actual_price": Decimal("299.00"),
        "offer_price": None,
        "currency": "INR",
        "is_active": True,
        "is_deleted": False,
    }
    data.update(overrides)

    return Plan(**data)
