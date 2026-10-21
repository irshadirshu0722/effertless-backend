from decimal import Decimal
from uuid import uuid4

import pytest

from tests.factories import make_plan_model


@pytest.mark.asyncio
async def test_list_active_returns_only_active_non_deleted_plans(
    db_session,
    plan_repo,
):
    db_session.add_all(
        [
            make_plan_model(
                code="pro",
                actual_price=Decimal("30.00"),
            ),
            make_plan_model(
                code="basic",
                actual_price=Decimal("10.00"),
            ),
            make_plan_model(
                code="inactive",
                is_active=False,
            ),
            make_plan_model(
                code="deleted",
                is_deleted=True,
            ),
        ]
    )
    await db_session.flush()

    plans = await plan_repo.list_active()

    assert {plan.code for plan in plans} == {"pro", "basic"}
    assert all(plan.is_active for plan in plans)
    assert all(not plan.is_deleted for plan in plans)


@pytest.mark.asyncio
async def test_list_active_orders_by_actual_price_ascending(
    db_session,
    plan_repo,
):
    db_session.add_all(
        [
            make_plan_model(
                code="premium",
                actual_price=Decimal("50.00"),
            ),
            make_plan_model(
                code="basic",
                actual_price=Decimal("10.00"),
            ),
            make_plan_model(
                code="standard",
                actual_price=Decimal("25.00"),
            ),
        ]
    )
    await db_session.flush()

    plans = await plan_repo.list_active()

    assert [plan.code for plan in plans] == [
        "basic",
        "standard",
        "premium",
    ]


@pytest.mark.asyncio
async def test_list_active_returns_empty_list_when_no_active_plans(
    db_session,
    plan_repo,
):
    db_session.add(
        make_plan_model(
            code="inactive",
            is_active=False,
        )
    )
    await db_session.flush()

    plans = await plan_repo.list_active()

    assert plans == []


@pytest.mark.asyncio
async def test_list_all_excludes_deleted_plans_by_default(
    db_session,
    plan_repo,
):
    db_session.add_all(
        [
            make_plan_model(code="basic"),
            make_plan_model(code="deleted", is_deleted=True),
        ]
    )
    await db_session.flush()

    plans = await plan_repo.list_all()

    assert {plan.code for plan in plans} == {"basic"}


@pytest.mark.asyncio
async def test_list_all_includes_deleted_plans_when_requested(
    db_session,
    plan_repo,
):
    db_session.add_all(
        [
            make_plan_model(code="basic"),
            make_plan_model(code="deleted", is_deleted=True),
        ]
    )
    await db_session.flush()

    plans = await plan_repo.list_all(include_deleted=True)

    assert {plan.code for plan in plans} == {"basic", "deleted"}


@pytest.mark.asyncio
async def test_list_all_filters_by_active_status(
    db_session,
    plan_repo,
):
    db_session.add_all(
        [
            make_plan_model(code="active", is_active=True),
            make_plan_model(code="inactive", is_active=False),
        ]
    )
    await db_session.flush()

    plans = await plan_repo.list_all(is_active=False)

    assert [plan.code for plan in plans] == ["inactive"]
    assert all(not plan.is_active for plan in plans)


@pytest.mark.asyncio
async def test_list_all_can_include_inactive_and_deleted_plans(
    db_session,
    plan_repo,
):
    db_session.add_all(
        [
            make_plan_model(code="active"),
            make_plan_model(
                code="inactive",
                is_active=False,
            ),
            make_plan_model(
                code="deleted",
                is_deleted=True,
            ),
        ]
    )
    await db_session.flush()

    plans = await plan_repo.list_all(
        include_deleted=True,
    )

    assert {plan.code for plan in plans} == {
        "active",
        "inactive",
        "deleted",
    }


@pytest.mark.asyncio
async def test_get_by_code_returns_matching_plan(
    db_session,
    plan_repo,
):
    db_session.add(make_plan_model(code="pro", name="Professional"))
    await db_session.flush()

    plan = await plan_repo.get_by_code("pro")

    assert plan is not None
    assert plan.code == "pro"
    assert plan.name == "Professional"
    assert plan.offer_price == Decimal("20.00")
    assert plan.currency == "PLN"


@pytest.mark.asyncio
async def test_get_by_code_returns_none_when_plan_does_not_exist(
    plan_repo,
):
    plan = await plan_repo.get_by_code("does-not-exist")

    assert plan is None


@pytest.mark.asyncio
async def test_get_by_code_does_not_return_deleted_plan(
    db_session,
    plan_repo,
):
    db_session.add(
        make_plan_model(
            code="deleted",
            is_deleted=True,
        )
    )
    await db_session.flush()

    plan = await plan_repo.get_by_code("deleted")

    assert plan is None


@pytest.mark.asyncio
async def test_get_by_id_returns_matching_plan(
    db_session,
    plan_repo,
):
    model = make_plan_model(code="pro", name="Professional")
    db_session.add(model)
    await db_session.flush()

    plan = await plan_repo.get_by_id(model.id)

    assert plan is not None
    assert plan.id == model.id
    assert plan.code == "pro"
    assert plan.name == "Professional"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_plan_does_not_exist(
    plan_repo,
):
    plan = await plan_repo.get_by_id(uuid4())

    assert plan is None


@pytest.mark.asyncio
async def test_save_persists_and_returns_plan(
    db_session,
    plan_repo,
):
    original_model = make_plan_model(
        code="new-plan",
        name="New Plan",
    )

    # Use the project's ORM-to-domain conversion to create a valid
    # domain object without duplicating the Plan constructor.
    plan_to_save = original_model.to_domain()

    saved_plan = await plan_repo.save(plan_to_save)

    assert saved_plan.id == plan_to_save.id
    assert saved_plan.code == "new-plan"
    assert saved_plan.name == "New Plan"

    # Verify the saved record can be read back from the database.
    loaded_plan = await plan_repo.get_by_code("new-plan")

    assert loaded_plan is not None
    assert loaded_plan.id == saved_plan.id
    assert loaded_plan.offer_price == Decimal("20.00")


@pytest.mark.asyncio
async def test_save_updates_existing_plan(
    db_session,
    plan_repo,
):
    original_model = make_plan_model(
        code="pro",
        name="Old Name",
    )
    db_session.add(original_model)
    await db_session.flush()

    existing_plan = original_model.to_domain()
    existing_plan.name = "Updated Name"

    saved_plan = await plan_repo.save(existing_plan)

    assert saved_plan.name == "Updated Name"

    loaded_plan = await plan_repo.get_by_code("pro")

    assert loaded_plan is not None
    assert loaded_plan.name == "Updated Name"
