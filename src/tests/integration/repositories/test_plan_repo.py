"""Integration tests for PostgresPlanRepository."""

from decimal import Decimal

import pytest

from app.domain.entities.plan import PlanCode
from tests.factories import make_plan_data

pytestmark = pytest.mark.asyncio


async def test_list_active_returns_only_active_non_deleted_plans(
    plan_repo,
) -> None:
    basic = await plan_repo.save(make_plan_data(code=PlanCode.BASIC))
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.STANDARD,
            is_active=False,
        )
    )
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.PRO,
            is_deleted=True,
        )
    )

    result = await plan_repo.list_active()

    assert [plan.code for plan in result] == [PlanCode.BASIC]
    assert basic.code in [plan.code for plan in result]


async def test_list_active_orders_by_actual_price(plan_repo) -> None:
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.BASIC,
            actual_price=Decimal("30.00"),
        )
    )
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.STANDARD,
            actual_price=Decimal("40.00"),
        )
    )
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.PRO,
            actual_price=Decimal("90.00"),
        )
    )

    result = await plan_repo.list_active()

    assert [plan.code for plan in result] == [
        PlanCode.BASIC,
        PlanCode.STANDARD,
        PlanCode.PRO,
    ]


async def test_list_all_excludes_deleted_by_default(plan_repo) -> None:
    await plan_repo.save(make_plan_data(code=PlanCode.BASIC))
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.PRO,
            is_deleted=True,
        )
    )

    result = await plan_repo.list_all()

    assert {plan.code for plan in result} == {PlanCode.BASIC}


async def test_list_all_can_include_deleted(plan_repo) -> None:
    await plan_repo.save(make_plan_data(code=PlanCode.BASIC))
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.PRO,
            is_deleted=True,
        )
    )

    result = await plan_repo.list_all(include_deleted=True)

    assert {plan.code for plan in result} == {
        PlanCode.BASIC,
        PlanCode.PRO,
    }


async def test_list_all_filters_by_active_status(plan_repo) -> None:
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.BASIC,
            is_active=True,
        )
    )
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.STANDARD,
            is_active=False,
        )
    )

    result = await plan_repo.list_all(is_active=False)

    assert [plan.code for plan in result] == [PlanCode.STANDARD]


async def test_get_by_code_returns_existing_plan(plan_repo) -> None:
    saved = await plan_repo.save(make_plan_data(code=PlanCode.PRO))

    result = await plan_repo.get_by_code(PlanCode.PRO.value)

    assert result is not None
    assert result.id == saved.id
    assert result.code is PlanCode.PRO


async def test_get_by_code_returns_none_for_missing_code(
    plan_repo,
) -> None:
    assert await plan_repo.get_by_code("UNKNOWN") is None


async def test_get_by_code_excludes_deleted_plan(plan_repo) -> None:
    await plan_repo.save(
        make_plan_data(
            code=PlanCode.PRO,
            is_deleted=True,
        )
    )

    assert await plan_repo.get_by_code(PlanCode.PRO.value) is None


async def test_get_by_id_returns_existing_plan(plan_repo) -> None:
    saved = await plan_repo.save(make_plan_data(code=PlanCode.BASIC))

    result = await plan_repo.get_by_id(saved.id)

    assert result is not None
    assert result.id == saved.id


async def test_get_by_id_returns_none_for_missing_plan(
    plan_repo,
) -> None:
    from uuid import uuid4

    assert await plan_repo.get_by_id(uuid4()) is None


async def test_save_persists_plan_fields(plan_repo) -> None:
    plan = make_plan_data(
        code=PlanCode.PRO,
        monthly_seconds=36000,
        actual_price=Decimal("100.00"),
        offer_price=Decimal("80.00"),
        currency="PLN",
    )

    saved = await plan_repo.save(plan)

    assert saved.id == plan.id
    assert saved.code is PlanCode.PRO
    assert saved.name == "Pro"
    assert saved.monthly_seconds == 36000
    assert saved.actual_price == Decimal("100.00")
    assert saved.offer_price == Decimal("80.00")
    assert saved.currency == "PLN"


async def test_save_updates_existing_plan(plan_repo) -> None:
    plan = await plan_repo.save(make_plan_data(code=PlanCode.PRO))

    plan.actual_price = Decimal("50.00")
    plan.monthly_seconds = 50000

    updated = await plan_repo.save(plan)

    assert updated.id == plan.id
    assert updated.code is PlanCode.PRO
    assert updated.name == "Pro"
    assert updated.actual_price == Decimal("50.00")
    assert updated.monthly_seconds == 50000

    fetched = await plan_repo.get_by_id(plan.id)

    assert fetched is not None
    assert fetched.actual_price == Decimal("50.00")
    assert fetched.monthly_seconds == 50000


async def test_update_modifies_existing_plan(plan_repo) -> None:
    plan = await plan_repo.save(make_plan_data(code=PlanCode.PRO))

    plan.actual_price = Decimal("120.00")
    plan.offer_price = Decimal("90.00")
    plan.monthly_seconds = 42000
    plan.is_active = False

    updated = await plan_repo.update(plan)

    assert updated.id == plan.id
    assert updated.name == "Pro"
    assert updated.actual_price == Decimal("120.00")
    assert updated.offer_price == Decimal("90.00")
    assert updated.monthly_seconds == 42000
    assert updated.is_active is False

    fetched = await plan_repo.get_by_id(plan.id)

    assert fetched is not None
    assert fetched.actual_price == Decimal("120.00")
    assert fetched.offer_price == Decimal("90.00")
    assert fetched.monthly_seconds == 42000
    assert fetched.is_active is False


async def test_update_raises_when_plan_does_not_exist(
    plan_repo,
) -> None:
    from uuid import uuid4

    plan = make_plan_data(code=PlanCode.PRO)
    plan.id = uuid4()

    with pytest.raises(ValueError, match="not found"):
        await plan_repo.update(plan)
