"""Integration tests for RedisUsageTracker against a real Redis container."""

from datetime import UTC, datetime

import pytest
from redis.asyncio import Redis

from app.adapters.redis_usage_tracker import RedisUsageTracker


@pytest.mark.asyncio
async def test_redis_usage_tracker_real_container(redis_client: Redis) -> None:
    tracker = RedisUsageTracker(redis_client, ttl_seconds=172800)
    user_id = "test_user_redis"
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    expected_key = f"usage:{user_id}:{today}"

    # 1. Cold start
    assert await tracker.get_today_usage(user_id) == 0
    # DIRECT REDIS CHECK: key should not exist initially
    assert await redis_client.get(expected_key) is None

    # 2. First increment
    count_1 = await tracker.increment_today_usage(user_id)
    assert count_1 == 1

    # DIRECT REDIS CHECK: Check raw Redis value
    raw_val = await redis_client.get(expected_key)
    assert raw_val == "1"

    # DIRECT REDIS CHECK: Check TTL set on key
    ttl = await redis_client.ttl(expected_key)
    assert 0 < ttl <= 172800

    # 3. Subsequent increments
    count_2 = await tracker.increment_today_usage(user_id)
    assert count_2 == 2

    # DIRECT REDIS CHECK: Raw value should be 2
    raw_val_2 = await redis_client.get(expected_key)
    assert raw_val_2 == "2"

    # 4. Independent user keys
    other_user = "other_user_redis"
    await tracker.increment_today_usage(other_user)

    assert await tracker.get_today_usage(user_id) == 2
    assert await tracker.get_today_usage(other_user) == 1

    # DIRECT REDIS CHECK: Both distinct keys exist in Redis
    assert await redis_client.get(expected_key) == "2"
    assert await redis_client.get(f"usage:{other_user}:{today}") == "1"


@pytest.mark.asyncio
async def test_redis_cache_real_container(redis_client: Redis) -> None:
    from app.adapters.redis_cache import RedisCache

    cache = RedisCache(redis_client)
    test_key = "user_cache_key_999"

    # 1. Non-existent key
    assert await cache.get(test_key) is None
    # DIRECT REDIS CHECK: Key absent
    assert await redis_client.get(test_key) is None

    # 2. Set key with TTL
    await cache.set(test_key, "cached_payload_data", ttl_seconds=120)
    assert await cache.get(test_key) == "cached_payload_data"

    # DIRECT REDIS CHECK: Raw value and TTL
    raw_val = await redis_client.get(test_key)
    assert raw_val == "cached_payload_data"
    ttl = await redis_client.ttl(test_key)
    assert 0 < ttl <= 120

    # 3. Delete key
    await cache.delete(test_key)
    assert await cache.get(test_key) is None

    # DIRECT REDIS CHECK: Key deleted
    assert await redis_client.get(test_key) is None


@pytest.mark.asyncio
async def test_check_entitlement_with_real_redis_and_postgres(
    db_session,
    redis_client: Redis,
) -> None:
    from datetime import timedelta
    from decimal import Decimal

    from app.adapters.postgres_subscription import PostgresSubscriptionRepository
    from app.application.use_case.check_entitlement import CheckEntitlementUseCase
    from app.core.config import Settings
    from app.core.exceptions import AudioExceedsTierLimitError, DailyQuotaExceededError
    from app.domain.entities.subscription import Subscription, SubscriptionStatus
    from app.domain.value_objects.plan_snapshot import PlanSnapshot

    sub_repo = PostgresSubscriptionRepository(db_session)
    tracker = RedisUsageTracker(redis_client, ttl_seconds=172800)
    use_case = CheckEntitlementUseCase(
        subscription_repo=sub_repo,
        usage_tracker=tracker,
        settings=Settings(
            free_tier_max_seconds=10,
            free_tier_max_requests_per_day=10,
        ),
    )

    free_user = "usr_free_gatekeeper"
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    free_key = f"usage:{free_user}:{today}"

    # 1. Free tier audio duration exceeded (15s > 10s) -> raises AudioExceedsTierLimitError
    with pytest.raises(AudioExceedsTierLimitError):
        await use_case.execute(user_id=free_user, audio_duration_seconds=15.0)

    # DIRECT REDIS CHECK: Usage counter was NOT incremented on rejected request
    assert await redis_client.get(free_key) is None

    # 2. Free tier audio duration within limit (8s <= 10s) -> allowed
    balance_1 = await use_case.execute(user_id=free_user, audio_duration_seconds=8.0)
    assert balance_1.used_today == 0
    assert balance_1.remaining == 10

    # Record usage upon completion
    new_count = await use_case.record_usage(free_user)
    assert new_count == 1

    # DIRECT REDIS CHECK: Counter incremented to 1
    assert await redis_client.get(free_key) == "1"

    # 3. Simulate usage up to 10
    for _ in range(9):
        await use_case.execute(user_id=free_user, audio_duration_seconds=5.0)
        await use_case.record_usage(free_user)

    # DIRECT REDIS CHECK: Counter reached daily limit 10
    assert await redis_client.get(free_key) == "10"

    # 4. 11th request -> raises DailyQuotaExceededError
    with pytest.raises(DailyQuotaExceededError):
        await use_case.execute(user_id=free_user, audio_duration_seconds=5.0)

    # DIRECT REDIS CHECK: Counter remains at 10 (not over-incremented)
    assert await redis_client.get(free_key) == "10"

    # 5. User on Paid Plan (Pro Plan: 120s limit, 150 req/day in PostgreSQL)
    paid_user = "usr_paid_gatekeeper"
    paid_key = f"usage:{paid_user}:{today}"
    now = datetime.now(UTC)

    pro_sub = Subscription(
        user_id=paid_user,
        status=SubscriptionStatus.ACTIVE,
        provider="cashfree",
        external_subscription_id="cf_pro_sub_gate",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=Decimal("599.00"),
        ),
    )
    await sub_repo.save(pro_sub)

    # Pro tier audio within limit (90s <= 120s) -> allowed
    paid_balance = await use_case.execute(user_id=paid_user, audio_duration_seconds=90.0)
    assert paid_balance.limit == 150
    assert paid_balance.used_today == 0
    assert paid_balance.remaining == 150

    await use_case.record_usage(paid_user)

    # DIRECT REDIS CHECK: Pro user counter is 1
    assert await redis_client.get(paid_key) == "1"

    # Pro tier audio exceeds limit (130s > 120s) -> raises AudioExceedsTierLimitError
    with pytest.raises(AudioExceedsTierLimitError):
        await use_case.execute(user_id=paid_user, audio_duration_seconds=130.0)

    # DIRECT REDIS CHECK: Pro user counter remains 1
    assert await redis_client.get(paid_key) == "1"
