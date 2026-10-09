"""Comprehensive API integration tests with real PostgreSQL and Redis containers."""

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres_subscription import PostgresPlanRepository
from app.core.config import Settings
from app.domain.entities.plan import BillingPeriod, Plan


def generate_webhook_signature(payload: bytes, secret: str, timestamp: str) -> str:
    message = timestamp.encode("utf-8") + payload
    return base64.b64encode(
        hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    ).decode("utf-8")


@pytest.mark.asyncio
async def test_health_and_readiness_probes_with_live_containers(
    integration_client: AsyncClient,
) -> None:
    """Test health liveness and readiness probes against running containers."""
    # 1. Liveness probe
    live_resp = await integration_client.get("/health")
    assert live_resp.status_code == 200
    assert live_resp.json() == {"status": "ok"}
    assert "X-Request-Id" in live_resp.headers

    # 2. Readiness probe (checks real TCP connections to Postgres and Redis containers)
    ready_resp = await integration_client.get("/health/ready")
    assert ready_resp.status_code == 200
    ready_data = ready_resp.json()
    assert ready_data["status"] == "ready"
    assert ready_data["dependencies"] == {
        "postgres": "connected",
        "redis": "connected",
    }


@pytest.mark.asyncio
async def test_get_plans_real_db_and_edge_cases(
    integration_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test listing plans with empty DB, inactive plans, and active sorted plans."""
    # 1. Empty database edge case
    empty_resp = await integration_client.get("/api/v1/subscriptions/plans")
    assert empty_resp.status_code == 200
    assert empty_resp.json() == {"plans": []}

    # 2. Seed various plans into real PostgreSQL
    plan_repo = PostgresPlanRepository(db_session)
    await plan_repo.save(
        Plan(
            code="pro_monthly",
            name="Pro",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("999.00"),
            offer_price=Decimal("599.00"),
            max_seconds_per_request=120,
            max_usage_per_day=150,
        )
    )
    await plan_repo.save(
        Plan(
            code="lite_monthly",
            name="Lite",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("499.00"),
            offer_price=Decimal("299.00"),
            max_seconds_per_request=30,
            max_usage_per_day=50,
        )
    )
    # Inactive plan - should be filtered out
    await plan_repo.save(
        Plan(
            code="inactive_plan",
            name="Inactive",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("199.00"),
            offer_price=Decimal("99.00"),
            max_seconds_per_request=10,
            max_usage_per_day=10,
            is_active=False,
        )
    )
    # Soft deleted plan - should be filtered out
    await plan_repo.save(
        Plan(
            code="deleted_plan",
            name="Deleted",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("99.00"),
            offer_price=Decimal("49.00"),
            max_seconds_per_request=5,
            max_usage_per_day=5,
            is_deleted=True,
        )
    )
    await db_session.commit()

    # Query active plans
    response = await integration_client.get("/api/v1/subscriptions/plans")
    assert response.status_code == 200
    data = response.json()
    assert len(data["plans"]) == 2
    # Verify sorted by actual_price ascending: Lite (499.00) before Pro (999.00)
    assert data["plans"][0]["code"] == "lite_monthly"
    assert data["plans"][0]["offer_price"] == 299.00
    assert data["plans"][1]["code"] == "pro_monthly"
    assert data["plans"][1]["offer_price"] == 599.00


@pytest.mark.asyncio
async def test_get_my_subscription_edge_cases(
    integration_client: AsyncClient,
    db_session: AsyncSession,
    redis_client: Redis,
) -> None:
    """Test /me endpoint: auth failures, trial, Redis counts, paid snapshot & immutability."""
    # Edge case 1: No authorization header
    unauth_resp = await integration_client.get("/api/v1/subscriptions/me")
    assert unauth_resp.status_code == 401
    assert unauth_resp.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    # Edge case 2: Malformed authorization header
    malformed_resp = await integration_client.get(
        "/api/v1/subscriptions/me",
        headers={"Authorization": "Basic badformat"},
    )
    assert malformed_resp.status_code == 401
    assert malformed_resp.json()["error"]["code"] == "INVALID_AUTH_TOKEN"

    # Edge case 3: Valid user without paid subscription (Free Tier default, zero usage)
    user_token = "user:usr_free_tier"
    free_resp = await integration_client.get(
        "/api/v1/subscriptions/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert free_resp.status_code == 200
    free_data = free_resp.json()
    assert free_data["status"] == "trialing"
    assert free_data["plan_name"] == "Free"
    assert free_data["limits"]["max_seconds_per_request"] == 10
    assert free_data["limits"]["max_usage_per_day"] == 10
    assert free_data["usage_today"]["used"] == 0
    assert free_data["usage_today"]["remaining"] == 10

    # Edge case 4: User has consumed usage directly in Redis
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    await redis_client.set(f"usage:usr_free_tier:{today}", "4")

    used_resp = await integration_client.get(
        "/api/v1/subscriptions/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert used_resp.status_code == 200
    used_data = used_resp.json()
    assert used_data["usage_today"]["used"] == 4
    assert used_data["usage_today"]["remaining"] == 6

    # Edge case 5: User has exceeded daily quota in Redis (remaining must never be negative)
    await redis_client.set(f"usage:usr_free_tier:{today}", "14")
    exceeded_resp = await integration_client.get(
        "/api/v1/subscriptions/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert exceeded_resp.status_code == 200
    assert exceeded_resp.json()["usage_today"]["used"] == 14
    assert exceeded_resp.json()["usage_today"]["remaining"] == 0

    # Edge case 6: User with active subscription and frozen snapshot
    paid_user = "user_paid_subscriber"
    paid_token = f"user:{paid_user}"
    await db_session.execute(
        sa.text(
            "INSERT INTO subscriptions (id, user_id, status, provider, external_subscription_id, "
            "current_period_start, current_period_end, snapshot_plan_name, snapshot_max_seconds, "
            "snapshot_max_usage_per_day, snapshot_price, snapshot_currency, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :uid, 'active', 'cashfree', 'cf_active_me_1', "
            "NOW(), NOW() + INTERVAL '30 days', 'Ultra Original', 300, 200, 999.00, 'INR', NOW(), NOW())"
        ),
        {"uid": paid_user},
    )
    await db_session.commit()

    paid_resp = await integration_client.get(
        "/api/v1/subscriptions/me",
        headers={"Authorization": f"Bearer {paid_token}"},
    )
    assert paid_resp.status_code == 200
    paid_sub = paid_resp.json()
    assert paid_sub["status"] == "active"
    assert paid_sub["plan_name"] == "Ultra Original"
    assert paid_sub["limits"]["max_seconds_per_request"] == 300
    assert paid_sub["limits"]["max_usage_per_day"] == 200
    assert paid_sub["usage_today"]["limit"] == 200
    assert paid_sub["usage_today"]["remaining"] == 200


@pytest.mark.asyncio
async def test_checkout_endpoint_edge_cases(
    integration_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test checkout session initiation, validations, and missing plan handling."""
    # Edge case 1: Unauthorized
    unauth = await integration_client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_code": "lite_monthly", "return_url": "https://return.url"},
    )
    assert unauth.status_code == 401

    # Edge case 2: Validation errors (missing required fields)
    user_token = "user:usr_checkout"
    missing_fields = await integration_client.post(
        "/api/v1/subscriptions/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"plan_code": "lite_monthly"},  # missing return_url
    )
    assert missing_fields.status_code == 400
    assert missing_fields.json()["error"]["code"] == "VALIDATION_ERROR"

    # Edge case 3: Non-existent plan
    not_found = await integration_client.post(
        "/api/v1/subscriptions/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"plan_code": "unknown_plan", "return_url": "https://return.url"},
    )
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "PLAN_NOT_FOUND"

    # Seed an inactive plan and a soft-deleted plan
    plan_repo = PostgresPlanRepository(db_session)
    await plan_repo.save(
        Plan(
            code="deleted_checkout_plan",
            name="Deleted",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("499.00"),
            offer_price=Decimal("299.00"),
            max_seconds_per_request=30,
            max_usage_per_day=50,
            is_deleted=True,
        )
    )
    await plan_repo.save(
        Plan(
            code="pro_monthly",
            name="Pro",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("999.00"),
            offer_price=Decimal("599.00"),
            max_seconds_per_request=120,
            max_usage_per_day=150,
        )
    )
    await db_session.commit()

    # Edge case 4: Soft-deleted plan rejected
    deleted_resp = await integration_client.post(
        "/api/v1/subscriptions/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"plan_code": "deleted_checkout_plan", "return_url": "https://return.url"},
    )
    assert deleted_resp.status_code == 404

    # Edge case 5: Successful checkout session
    success = await integration_client.post(
        "/api/v1/subscriptions/checkout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"plan_code": "pro_monthly", "return_url": "https://return.url"},
    )
    assert success.status_code == 200
    res_data = success.json()
    assert res_data["subscription_id"].startswith("sub_")
    assert "payment_link" in res_data
    assert res_data["status"] == "pending"


@pytest.mark.asyncio
async def test_webhook_full_lifecycle_and_direct_db_verification(
    integration_client: AsyncClient,
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    """Test webhook verification, idempotency, direct DB rows, and cancellation."""
    # 1. Seed plan into PostgreSQL
    plan_repo = PostgresPlanRepository(db_session)
    await plan_repo.save(
        Plan(
            code="lite_webhook_test",
            name="Lite Webhook",
            billing_period=BillingPeriod.MONTHLY,
            actual_price=Decimal("499.00"),
            offer_price=Decimal("299.00"),
            max_seconds_per_request=30,
            max_usage_per_day=50,
        )
    )
    await db_session.commit()

    secret = test_settings.cashfree_webhook_secret
    timestamp = "1728000000"
    ext_sub_id = f"cf_sub_{uuid.uuid4().hex[:12]}"
    user_id = "user_webhook_payer"

    event_payload = {
        "event_id": f"evt_act_{uuid.uuid4().hex[:8]}",
        "type": "SUBSCRIPTION_ACTIVATION",
        "data": {
            "subscription_id": ext_sub_id,
            "customer_id": user_id,
            "plan_id": "lite_webhook_test",
        },
    }
    raw_body = json.dumps(event_payload).encode("utf-8")

    # Edge case 1: Missing signature headers
    no_sig_resp = await integration_client.post(
        "/api/v1/subscriptions/webhook",
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )
    assert no_sig_resp.status_code == 401
    assert no_sig_resp.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"

    # Edge case 2: Bad signature rejected
    bad_resp = await integration_client.post(
        "/api/v1/subscriptions/webhook",
        content=raw_body,
        headers={
            "x-webhook-signature": "invalid_sig",
            "x-webhook-timestamp": timestamp,
            "Content-Type": "application/json",
        },
    )
    assert bad_resp.status_code == 401
    assert bad_resp.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"

    # Edge case 3: Tampered payload (signature from different body)
    valid_sig = generate_webhook_signature(raw_body, secret, timestamp)
    tampered_body = json.dumps({"tampered": True}).encode("utf-8")
    tampered_resp = await integration_client.post(
        "/api/v1/subscriptions/webhook",
        content=tampered_body,
        headers={
            "x-webhook-signature": valid_sig,
            "x-webhook-timestamp": timestamp,
            "Content-Type": "application/json",
        },
    )
    assert tampered_resp.status_code == 401

    # Edge case 4: Valid signature processed successfully
    good_resp = await integration_client.post(
        "/api/v1/subscriptions/webhook",
        content=raw_body,
        headers={
            "x-webhook-signature": valid_sig,
            "x-webhook-timestamp": timestamp,
            "Content-Type": "application/json",
        },
    )
    assert good_resp.status_code == 200
    assert good_resp.json() == {"status": "acknowledged"}

    # DIRECT DB CHECK: Verify subscription record and frozen snapshot in PostgreSQL
    db_session.expire_all()
    result = await db_session.execute(
        sa.text(
            "SELECT user_id, status, external_subscription_id, snapshot_plan_name, "
            "snapshot_max_seconds, snapshot_max_usage_per_day, snapshot_price "
            "FROM subscriptions WHERE external_subscription_id = :sid"
        ),
        {"sid": ext_sub_id},
    )

    sub_row = result.mappings().one()
    assert sub_row["user_id"] == user_id
    assert sub_row["status"] == "active"
    assert sub_row["snapshot_plan_name"] == "Lite Webhook"
    assert sub_row["snapshot_max_seconds"] == 30
    assert sub_row["snapshot_max_usage_per_day"] == 50
    assert sub_row["snapshot_price"] == Decimal("299.00")

    # DIRECT DB CHECK: Verify event was recorded in audit table
    evt_check = await db_session.execute(
        sa.text("SELECT event_id, status FROM subscription_webhook_events WHERE event_id = :eid"),
        {"eid": event_payload["event_id"]},
    )
    assert evt_check.mappings().one()["status"] == "processed"

    # Edge case 5: Duplicate webhook delivery (Idempotency)
    dup_resp = await integration_client.post(
        "/api/v1/subscriptions/webhook",
        content=raw_body,
        headers={
            "x-webhook-signature": valid_sig,
            "x-webhook-timestamp": timestamp,
            "Content-Type": "application/json",
        },
    )
    assert dup_resp.status_code == 200

    # DIRECT DB CHECK: Exactly one subscription row exists (no duplicate inserts)
    count_check = await db_session.execute(
        sa.text("SELECT COUNT(*) FROM subscriptions WHERE external_subscription_id = :sid"),
        {"sid": ext_sub_id},
    )
    assert count_check.scalar_one() == 1

    # Edge case 6: Webhook Cancellation Event
    cancel_payload = {
        "event_id": f"evt_cancel_{uuid.uuid4().hex[:8]}",
        "type": "SUBSCRIPTION_CANCELLED",
        "data": {
            "subscription_id": ext_sub_id,
        },
    }
    cancel_raw = json.dumps(cancel_payload).encode("utf-8")
    cancel_sig = generate_webhook_signature(cancel_raw, secret, timestamp)

    cancel_resp = await integration_client.post(
        "/api/v1/subscriptions/webhook",
        content=cancel_raw,
        headers={
            "x-webhook-signature": cancel_sig,
            "x-webhook-timestamp": timestamp,
            "Content-Type": "application/json",
        },
    )
    assert cancel_resp.status_code == 200

    # DIRECT DB CHECK: Subscription status transitioned to cancelled in DB
    db_session.expire_all()
    cancelled_check = await db_session.execute(
        sa.text(
            "SELECT status, cancelled_at FROM subscriptions WHERE external_subscription_id = :sid"
        ),
        {"sid": ext_sub_id},
    )

    cancelled_row = cancelled_check.mappings().one()
    assert cancelled_row["status"] == "cancelled"
    assert cancelled_row["cancelled_at"] is not None

    # Edge case 7: Unknown event type handled safely
    unknown_payload = {
        "event_id": f"evt_unknown_{uuid.uuid4().hex[:8]}",
        "type": "UNKNOWN_PAYMENT_EVENT",
        "data": {"foo": "bar"},
    }
    unknown_raw = json.dumps(unknown_payload).encode("utf-8")
    unknown_sig = generate_webhook_signature(unknown_raw, secret, timestamp)

    unknown_resp = await integration_client.post(
        "/api/v1/subscriptions/webhook",
        content=unknown_raw,
        headers={
            "x-webhook-signature": unknown_sig,
            "x-webhook-timestamp": timestamp,
            "Content-Type": "application/json",
        },
    )
    assert unknown_resp.status_code == 200
    assert unknown_resp.json() == {"status": "acknowledged"}

    # DIRECT DB CHECK: Unknown event recorded in webhook audit table
    db_session.expire_all()
    unknown_check = await db_session.execute(
        sa.text("SELECT status FROM subscription_webhook_events WHERE event_id = :eid"),
        {"eid": unknown_payload["event_id"]},
    )
    assert unknown_check.mappings().one()["status"] == "processed"


@pytest.mark.asyncio
async def test_cancel_endpoint_direct_db_check(
    integration_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test /cancel endpoint: unauthenticated, no subscription, active subscription & direct DB check."""
    # Edge case 1: Missing auth header
    unauth = await integration_client.post("/api/v1/subscriptions/cancel")
    assert unauth.status_code == 401

    # Edge case 2: User without any active subscription
    free_token = "user:usr_cancel_none"
    no_sub_resp = await integration_client.post(
        "/api/v1/subscriptions/cancel",
        headers={"Authorization": f"Bearer {free_token}"},
    )
    assert no_sub_resp.status_code == 200
    assert no_sub_resp.json() == {"status": "cancelled", "current_period_end": None}

    # Edge case 3: User with active subscription in DB
    user_id = "user_cancel_api_test"
    ext_id = f"cf_sub_{uuid.uuid4().hex[:8]}"

    await db_session.execute(
        sa.text(
            "INSERT INTO subscriptions (id, user_id, status, provider, external_subscription_id, "
            "current_period_start, current_period_end, snapshot_plan_name, snapshot_max_seconds, "
            "snapshot_max_usage_per_day, snapshot_price, snapshot_currency, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :uid, 'active', 'cashfree', :ext_id, "
            "NOW(), NOW() + INTERVAL '30 days', 'Pro', 120, 150, 599.00, 'INR', NOW(), NOW())"
        ),
        {"uid": user_id, "ext_id": ext_id},
    )
    await db_session.commit()

    # Call /cancel endpoint
    user_token = f"user:{user_id}"
    cancel_resp = await integration_client.post(
        "/api/v1/subscriptions/cancel",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
    assert cancel_resp.json()["current_period_end"] is not None

    # DIRECT DB CHECK: Verify status in database is cancelled
    db_session.expire_all()
    check = await db_session.execute(
        sa.text("SELECT status FROM subscriptions WHERE user_id = :uid"),
        {"uid": user_id},
    )
    assert check.scalar_one() == "cancelled"

    # Verify that subsequent GET /me reflects free tier
    me_resp = await integration_client.get(
        "/api/v1/subscriptions/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["status"] == "trialing"
    assert me_resp.json()["plan_name"] == "Free"
