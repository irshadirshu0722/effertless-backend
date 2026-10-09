"""Integration tests for PostgreSQL repositories against a real database container."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres_subscription import (
    PostgresPlanRepository,
    PostgresSubscriptionRepository,
    PostgresWebhookEventRepository,
)
from app.domain.entities.plan import BillingPeriod, Plan
from app.domain.entities.subscription import Subscription, SubscriptionStatus
from app.domain.value_objects.plan_snapshot import PlanSnapshot


@pytest.mark.asyncio
async def test_plan_repository_save_and_direct_db_check(db_session: AsyncSession) -> None:
    repo = PostgresPlanRepository(db_session)
    plan = Plan(
        code="ultra_monthly",
        name="Ultra",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("1499.00"),
        offer_price=Decimal("999.00"),
        max_seconds_per_request=300,
        max_usage_per_day=200,
    )

    saved_plan = await repo.save(plan)
    assert saved_plan.code == "ultra_monthly"

    # DIRECT DB CHECK: Query database directly using raw SQL
    result = await db_session.execute(
        sa.text(
            "SELECT code, name, actual_price, offer_price, max_seconds_per_request, "
            "max_usage_per_day, is_active, is_deleted FROM plans WHERE code = :code"
        ),
        {"code": "ultra_monthly"},
    )
    row = result.mappings().one()
    assert row["code"] == "ultra_monthly"
    assert row["name"] == "Ultra"
    assert row["actual_price"] == Decimal("1499.00")
    assert row["offer_price"] == Decimal("999.00")
    assert row["max_seconds_per_request"] == 300
    assert row["max_usage_per_day"] == 200
    assert row["is_active"] is True
    assert row["is_deleted"] is False


@pytest.mark.asyncio
async def test_plan_repository_list_active_filters_inactive_and_deleted(
    db_session: AsyncSession,
) -> None:
    repo = PostgresPlanRepository(db_session)

    # 1. Active lower price
    await repo.save(
        Plan(
            code="lite",
            name="Lite",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("499.00"),
            offer_price=Decimal("299.00"),
            max_seconds_per_request=30,
            max_usage_per_day=50,
        )
    )
    # 2. Active higher price
    await repo.save(
        Plan(
            code="pro",
            name="Pro",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("999.00"),
            offer_price=Decimal("599.00"),
            max_seconds_per_request=120,
            max_usage_per_day=150,
        )
    )
    # 3. Inactive plan
    await repo.save(
        Plan(
            code="archived",
            name="Archived",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("199.00"),
            offer_price=Decimal("99.00"),
            max_seconds_per_request=10,
            max_usage_per_day=10,
            is_active=False,
        )
    )
    # 4. Soft-deleted plan
    await repo.save(
        Plan(
            code="deleted",
            name="Deleted",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("199.00"),
            offer_price=Decimal("99.00"),
            max_seconds_per_request=10,
            max_usage_per_day=10,
            is_deleted=True,
        )
    )

    plans = await repo.list_active()
    assert len(plans) == 2
    assert [p.code for p in plans] == ["lite", "pro"]  # Sorted by actual_price asc


@pytest.mark.asyncio
async def test_subscription_repository_save_and_direct_db_check(
    db_session: AsyncSession,
) -> None:
    plan_repo = PostgresPlanRepository(db_session)
    plan = await plan_repo.save(
        Plan(
            code="pro_sub_plan",
            name="Pro Plan",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("999.00"),
            offer_price=Decimal("599.00"),
            max_seconds_per_request=120,
            max_usage_per_day=150,
        )
    )

    sub_repo = PostgresSubscriptionRepository(db_session)
    now = datetime.now(UTC)
    sub = Subscription(
        user_id="user_postgres_test",
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        provider="cashfree",
        external_subscription_id="cf_sub_pg_123",
        external_customer_id="cf_cust_123",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        snapshot=PlanSnapshot(
            plan_name="Pro Plan",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=Decimal("599.00"),
            currency="INR",
        ),
    )

    await sub_repo.save(sub)

    # DIRECT DB CHECK: Verify snapshot fields and subscription details in DB
    result = await db_session.execute(
        sa.text(
            "SELECT user_id, status, external_subscription_id, snapshot_plan_name, "
            "snapshot_max_seconds, snapshot_max_usage_per_day, snapshot_price, snapshot_currency "
            "FROM subscriptions WHERE external_subscription_id = :ext_id"
        ),
        {"ext_id": "cf_sub_pg_123"},
    )
    row = result.mappings().one()
    assert row["user_id"] == "user_postgres_test"
    assert row["status"] == "active"
    assert row["snapshot_plan_name"] == "Pro Plan"
    assert row["snapshot_max_seconds"] == 120
    assert row["snapshot_max_usage_per_day"] == 150
    assert row["snapshot_price"] == Decimal("599.00")
    assert row["snapshot_currency"] == "INR"


@pytest.mark.asyncio
async def test_subscription_repository_get_active_and_cancelled(
    db_session: AsyncSession,
) -> None:
    sub_repo = PostgresSubscriptionRepository(db_session)
    now = datetime.now(UTC)
    sub = Subscription(
        user_id="user_active_check",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        snapshot=PlanSnapshot(
            plan_name="Lite",
            max_seconds_per_request=30,
            max_usage_per_day=50,
            price=Decimal("299.00"),
        ),
        external_subscription_id="cf_active_001",
    )
    await sub_repo.save(sub)

    # Active subscription lookup
    found = await sub_repo.get_active_by_user_id("user_active_check")
    assert found is not None
    assert found.status == SubscriptionStatus.ACTIVE

    # Directly cancel in database
    await db_session.execute(
        sa.text("UPDATE subscriptions SET status = 'cancelled' WHERE user_id = :uid"),
        {"uid": "user_active_check"},
    )
    await db_session.flush()

    # Should no longer return as active
    found_after_cancel = await sub_repo.get_active_by_user_id("user_active_check")
    assert found_after_cancel is None


@pytest.mark.asyncio
async def test_webhook_event_repository_idempotency_and_db_check(
    db_session: AsyncSession,
) -> None:
    repo = PostgresWebhookEventRepository(db_session)
    event_id = f"evt_{uuid4().hex}"

    assert await repo.has_been_processed(event_id) is False

    await repo.record_event(
        event_id=event_id,
        event_type="SUBSCRIPTION_CHARGED",
        payload={"amount": 599.0, "currency": "INR"},
        status="processed",
    )

    # Check has_been_processed
    assert await repo.has_been_processed(event_id) is True

    # DIRECT DB CHECK: Verify event record and JSON payload in database
    result = await db_session.execute(
        sa.text(
            "SELECT event_id, event_type, status, payload "
            "FROM subscription_webhook_events WHERE event_id = :eid"
        ),
        {"eid": event_id},
    )
    row = result.mappings().one()
    assert row["event_id"] == event_id
    assert row["event_type"] == "SUBSCRIPTION_CHARGED"
    assert row["status"] == "processed"
    assert row["payload"] == {"amount": 599.0, "currency": "INR"}


@pytest.mark.asyncio
async def test_plan_repository_update_existing_and_direct_db_check(
    db_session: AsyncSession,
) -> None:
    repo = PostgresPlanRepository(db_session)
    plan = Plan(
        code="standard_monthly",
        name="Standard",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("499.00"),
        offer_price=Decimal("299.00"),
        max_seconds_per_request=30,
        max_usage_per_day=50,
    )
    saved = await repo.save(plan)

    # DIRECT DB CHECK: Row was inserted
    res_initial = await db_session.execute(
        sa.text("SELECT id, name, offer_price FROM plans WHERE code = :code"),
        {"code": "standard_monthly"},
    )
    row_initial = res_initial.mappings().one()
    assert row_initial["name"] == "Standard"
    assert row_initial["offer_price"] == Decimal("299.00")

    # Update plan details
    updated_plan = Plan(
        id=saved.id,
        code=saved.code,
        name="Standard Super",
        billing_period=saved.billing_period,
        actual_price=Decimal("599.00"),
        offer_price=Decimal("349.00"),
        max_seconds_per_request=45,
        max_usage_per_day=75,
        is_active=True,
        is_deleted=False,
    )
    await repo.save(updated_plan)

    # DIRECT DB CHECK: Existing row updated in place (no duplicate row)
    count_res = await db_session.execute(
        sa.text("SELECT COUNT(*) FROM plans WHERE code = :code"),
        {"code": "standard_monthly"},
    )
    assert count_res.scalar_one() == 1

    res_updated = await db_session.execute(
        sa.text(
            "SELECT name, actual_price, offer_price, max_seconds_per_request, max_usage_per_day "
            "FROM plans WHERE id = :pid"
        ),
        {"pid": saved.id},
    )
    row_updated = res_updated.mappings().one()
    assert row_updated["name"] == "Standard Super"
    assert row_updated["actual_price"] == Decimal("599.00")
    assert row_updated["offer_price"] == Decimal("349.00")
    assert row_updated["max_seconds_per_request"] == 45
    assert row_updated["max_usage_per_day"] == 75


@pytest.mark.asyncio
async def test_plan_repository_get_by_id_and_code_edge_cases(
    db_session: AsyncSession,
) -> None:
    repo = PostgresPlanRepository(db_session)
    plan = await repo.save(
        Plan(
            code="test_edge_code",
            name="Edge Plan",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("200.00"),
            offer_price=Decimal("100.00"),
            max_seconds_per_request=15,
            max_usage_per_day=20,
        )
    )

    # 1. get_by_id found
    found_by_id = await repo.get_by_id(plan.id)
    assert found_by_id is not None
    assert found_by_id.code == "test_edge_code"

    # 2. get_by_id not found with random UUID
    missing_by_id = await repo.get_by_id(uuid4())
    assert missing_by_id is None

    # 3. get_by_code found
    found_by_code = await repo.get_by_code("test_edge_code")
    assert found_by_code is not None
    assert found_by_code.id == plan.id

    # 4. get_by_code not found
    missing_by_code = await repo.get_by_code("non_existent_plan_code")
    assert missing_by_code is None

    # 5. get_by_code ignores soft-deleted plan
    soft_deleted_plan = await repo.save(
        Plan(
            code="soft_deleted_code",
            name="Soft Deleted",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("200.00"),
            offer_price=Decimal("100.00"),
            max_seconds_per_request=15,
            max_usage_per_day=20,
            is_deleted=True,
        )
    )
    deleted_lookup = await repo.get_by_code(soft_deleted_plan.code)
    assert deleted_lookup is None


@pytest.mark.asyncio
async def test_subscription_repository_update_status_and_direct_db_check(
    db_session: AsyncSession,
) -> None:
    sub_repo = PostgresSubscriptionRepository(db_session)
    now = datetime.now(UTC)
    sub = Subscription(
        user_id="user_update_sub",
        status=SubscriptionStatus.ACTIVE,
        provider="cashfree",
        external_subscription_id="cf_sub_update_1",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=Decimal("599.00"),
        ),
    )
    saved = await sub_repo.save(sub)

    # DIRECT DB CHECK: Active status in DB
    init_res = await db_session.execute(
        sa.text("SELECT status, cancelled_at FROM subscriptions WHERE id = :sid"),
        {"sid": saved.id},
    )
    init_row = init_res.mappings().one()
    assert init_row["status"] == "active"
    assert init_row["cancelled_at"] is None

    # Update subscription to cancelled
    cancel_time = datetime.now(UTC)
    updated_sub = Subscription(
        id=saved.id,
        user_id=saved.user_id,
        status=SubscriptionStatus.CANCELLED,
        provider=saved.provider,
        external_subscription_id=saved.external_subscription_id,
        current_period_start=saved.current_period_start,
        current_period_end=saved.current_period_end,
        cancelled_at=cancel_time,
        snapshot=saved.snapshot,
    )
    await sub_repo.save(updated_sub)

    # DIRECT DB CHECK: Row updated in place
    db_check = await db_session.execute(
        sa.text("SELECT status, cancelled_at FROM subscriptions WHERE id = :sid"),
        {"sid": saved.id},
    )
    db_row = db_check.mappings().one()
    assert db_row["status"] == "cancelled"
    assert db_row["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_subscription_repository_trialing_expired_and_multiple_ordering(
    db_session: AsyncSession,
) -> None:
    sub_repo = PostgresSubscriptionRepository(db_session)
    now = datetime.now(UTC)

    # 1. Trialing subscription returns as active
    trial_sub = Subscription(
        user_id="user_trial",
        status=SubscriptionStatus.TRIALING,
        current_period_start=now,
        current_period_end=now + timedelta(days=7),
        snapshot=PlanSnapshot(
            plan_name="Trial",
            max_seconds_per_request=10,
            max_usage_per_day=10,
            price=Decimal("0.00"),
        ),
        external_subscription_id="cf_trial_01",
    )
    await sub_repo.save(trial_sub)
    found_trial = await sub_repo.get_active_by_user_id("user_trial")
    assert found_trial is not None
    assert found_trial.status == SubscriptionStatus.TRIALING

    # 2. Expired status is ignored
    expired_sub = Subscription(
        user_id="user_expired",
        status=SubscriptionStatus.EXPIRED,
        current_period_start=now - timedelta(days=60),
        current_period_end=now - timedelta(days=30),
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=Decimal("599.00"),
        ),
        external_subscription_id="cf_expired_01",
    )
    await sub_repo.save(expired_sub)
    found_expired = await sub_repo.get_active_by_user_id("user_expired")
    assert found_expired is None

    # 3. User with multiple subscriptions returns newest active one
    multi_user = "user_multi_subs"
    older_cancelled = Subscription(
        user_id=multi_user,
        status=SubscriptionStatus.CANCELLED,
        current_period_start=now - timedelta(days=60),
        current_period_end=now - timedelta(days=30),
        snapshot=PlanSnapshot(
            plan_name="Lite",
            max_seconds_per_request=30,
            max_usage_per_day=50,
            price=Decimal("299.00"),
        ),
        external_subscription_id="cf_old_01",
    )
    newer_active = Subscription(
        user_id=multi_user,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=Decimal("599.00"),
        ),
        external_subscription_id="cf_new_02",
    )
    await sub_repo.save(older_cancelled)
    await sub_repo.save(newer_active)

    found_multi = await sub_repo.get_active_by_user_id(multi_user)
    assert found_multi is not None
    assert found_multi.external_subscription_id == "cf_new_02"
    assert found_multi.snapshot.plan_name == "Pro"

    # 4. get_by_external_id checks
    found_ext = await sub_repo.get_by_external_id("cf_new_02")
    assert found_ext is not None
    assert found_ext.user_id == multi_user

    missing_ext = await sub_repo.get_by_external_id("non_existent_ext_id")
    assert missing_ext is None
