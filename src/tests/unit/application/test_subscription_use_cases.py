"""Unit tests for subscription application use cases."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from app.application.use_case.check_entitlement import CheckEntitlementUseCase
from app.application.use_case.list_plans import ListPlansUseCase
from app.application.use_case.subscription.get_user_subscription import GetUserSubscriptionUseCase
from app.application.use_case.subscription.initiate_checkout import InitiateCheckoutUseCase
from app.application.use_case.subscription.webhook_verification import (
    HandleSubscriptionWebhookUseCase,
)
from app.core.config import Settings
from app.core.exceptions import (
    ActiveSubscriptionError,
    AudioExceedsTierLimitError,
    DailyQuotaExceededError,
    InvalidWebhookSignatureError,
    PlanNotFoundError,
)
from app.domain.entities.authenticated_user import AuthenticatedUser
from app.domain.entities.plan import BillingPeriod, Plan
from app.domain.entities.subscription import Subscription, SubscriptionStatus
from app.domain.value_objects.plan_snapshot import PlanSnapshot
from app.ports.subscription import (
    PaymentGateway,
    PlanRepository,
    SubscriptionRepository,
    UsageTracker,
    WebhookEventRepository,
)


class InMemoryPlanRepo(PlanRepository):
    def __init__(self, plans: list[Plan]) -> None:
        self.plans = {p.code: p for p in plans}

    async def list_active(self) -> Sequence[Plan]:
        return [p for p in self.plans.values() if p.is_active and not p.is_deleted]

    async def get_by_code(self, code: str) -> Plan | None:
        return self.plans.get(code)

    async def get_by_id(self, plan_id: UUID) -> Plan | None:
        for p in self.plans.values():
            if p.id == plan_id:
                return p
        return None

    async def save(self, plan: Plan) -> Plan:
        self.plans[plan.code] = plan
        return plan


class InMemorySubscriptionRepo(SubscriptionRepository):
    def __init__(self) -> None:
        self.subs_by_user: dict[str, Subscription] = {}
        self.subs_by_ext_id: dict[str, Subscription] = {}

    async def get_active_by_user_id(self, user_id: str) -> Subscription | None:
        sub = self.subs_by_user.get(user_id)
        if sub and sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
            return sub
        return None

    async def get_latest_by_user_id(self, user_id: str) -> Subscription | None:
        return self.subs_by_user.get(user_id)

    async def get_by_external_id(self, external_id: str) -> Subscription | None:
        return self.subs_by_ext_id.get(external_id)

    async def save(self, subscription: Subscription) -> Subscription:
        self.subs_by_user[subscription.user_id] = subscription
        if subscription.external_subscription_id:
            self.subs_by_ext_id[subscription.external_subscription_id] = subscription
        return subscription


class InMemoryUsageTracker(UsageTracker):
    def __init__(self, initial_usage: int = 0) -> None:
        self.usage: dict[str, int] = {}
        self._initial = initial_usage

    async def get_today_usage(self, user_id: str) -> int:
        return self.usage.get(user_id, self._initial)

    async def increment_today_usage(self, user_id: str) -> int:
        count = self.usage.get(user_id, self._initial) + 1
        self.usage[user_id] = count
        return count


class FakePaymentGateway(PaymentGateway):
    def __init__(self, valid_sig: bool = True) -> None:
        self.valid_sig = valid_sig
        self.created_plans: list[str] = []
        self.deleted_plans: list[str] = []
        self.cancelled_ids: list[str] = []
        self.last_first_charge_time: datetime | None = None

    async def create_plan(self, plan: Plan) -> bool:
        self.created_plans.append(plan.code)
        return True

    async def delete_plan(self, plan_code: str) -> bool:
        self.deleted_plans.append(plan_code)
        return True

    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str | None,
        plan: Plan,
        return_url: str,
        first_charge_time: datetime | None = None,
    ) -> tuple[str, str]:
        self.last_first_charge_time = first_charge_time
        sub_id = f"sub_fake_{plan.code}"
        return sub_id, f"session_fake_{plan.code}"

    async def cancel_subscription(self, external_subscription_id: str) -> bool:
        self.cancelled_ids.append(external_subscription_id)
        return True

    def verify_webhook_signature(
        self,
        raw_payload: bytes,
        signature: str,
        timestamp: str,
    ) -> bool:
        return self.valid_sig


class InMemoryWebhookRepo(WebhookEventRepository):
    def __init__(self) -> None:
        self.events: set[str] = set()

    async def has_been_processed(self, event_id: str) -> bool:
        return event_id in self.events

    async def record_event(
        self,
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        status: str,
    ) -> None:
        self.events.add(event_id)


@pytest.fixture
def sample_plan() -> Plan:
    return Plan(
        code="pro_monthly",
        name="Pro",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("999.00"),
        offer_price=Decimal("599.00"),
        max_seconds_per_request=120,
        max_usage_per_day=150,
    )


@pytest.mark.asyncio
async def test_list_plans_use_case(sample_plan: Plan) -> None:
    repo = InMemoryPlanRepo([sample_plan])
    uc = ListPlansUseCase(repo)
    plans = await uc.execute()
    assert len(plans) == 1
    assert plans[0].code == "pro_monthly"


@pytest.mark.asyncio
async def test_get_user_subscription_free_tier(sample_plan: Plan) -> None:
    sub_repo = InMemorySubscriptionRepo()
    usage_tracker = InMemoryUsageTracker(initial_usage=4)
    settings = Settings(free_tier_max_seconds=10, free_tier_max_requests_per_day=10)

    uc = GetUserSubscriptionUseCase(sub_repo, usage_tracker, settings)
    details = await uc.execute("user-free")

    assert details.status == "trialing"
    assert details.plan_name == "Free"
    assert details.limits.max_seconds_per_request == 10
    assert details.limits.max_usage_per_day == 10
    assert details.usage_today.used_today == 4
    assert details.usage_today.remaining == 6


@pytest.mark.asyncio
async def test_get_user_subscription_active_subscriber(sample_plan: Plan) -> None:
    sub_repo = InMemorySubscriptionRepo()
    usage_tracker = InMemoryUsageTracker(initial_usage=20)
    settings = Settings()

    now = datetime.now(UTC)
    sub = Subscription(
        user_id="user-pro",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=2),
        current_period_end=now + timedelta(days=28),
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=Decimal("599.00"),
        ),
    )
    await sub_repo.save(sub)

    uc = GetUserSubscriptionUseCase(sub_repo, usage_tracker, settings)
    details = await uc.execute("user-pro")

    assert details.status == "active"
    assert details.plan_name == "Pro"
    assert details.limits.max_seconds_per_request == 120
    assert details.usage_today.used_today == 20
    assert details.usage_today.remaining == 130


@pytest.mark.asyncio
async def test_initiate_checkout_success(sample_plan: Plan) -> None:
    plan_repo = InMemoryPlanRepo([sample_plan])
    gateway = FakePaymentGateway()
    user = AuthenticatedUser(user_id="user-1", email="u1@test.com")

    uc = InitiateCheckoutUseCase(plan_repo, gateway)
    result = await uc.execute(user, "pro_monthly", "https://return.url")

    assert result.subscription_id == "sub_fake_pro_monthly"
    assert result.checkout_session_id == "session_fake_pro_monthly"
    assert gateway.last_first_charge_time is None


@pytest.mark.asyncio
async def test_initiate_checkout_unknown_plan() -> None:
    plan_repo = InMemoryPlanRepo([])
    gateway = FakePaymentGateway()
    user = AuthenticatedUser(user_id="user-1")

    uc = InitiateCheckoutUseCase(plan_repo, gateway)
    with pytest.raises(PlanNotFoundError):
        await uc.execute(user, "non_existent", "https://return.url")


@pytest.mark.asyncio
async def test_initiate_checkout_downgrade(sample_plan: Plan) -> None:
    cheaper_plan = Plan(
        code="basic_monthly",
        name="Basic",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("499.00"),
        offer_price=Decimal("199.00"),
        max_seconds_per_request=30,
        max_usage_per_day=30,
    )
    plan_repo = InMemoryPlanRepo([sample_plan, cheaper_plan])
    sub_repo = InMemorySubscriptionRepo()
    gateway = FakePaymentGateway()
    user = AuthenticatedUser(user_id="user-downgrade", email="down@test.com")

    now = datetime.now(UTC)
    period_end = now + timedelta(days=20)
    current_sub = Subscription(
        user_id=user.user_id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=10),
        current_period_end=period_end,
        external_subscription_id="sub_current_pro",
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=sample_plan.offer_price,  # 599.00
        ),
    )
    await sub_repo.save(current_sub)

    uc = InitiateCheckoutUseCase(plan_repo, gateway, sub_repo)
    result = await uc.execute(user, "basic_monthly", "https://return.url")

    assert result.subscription_id == "sub_fake_basic_monthly"
    assert result.checkout_session_id == "session_fake_basic_monthly"
    # Future recurring payment scheduled at current period end
    assert gateway.last_first_charge_time == period_end
    # Current subscription should NOT be cancelled
    assert len(gateway.cancelled_ids) == 0
    active_in_repo = await sub_repo.get_active_by_user_id(user.user_id)
    assert active_in_repo is not None
    assert active_in_repo.status == SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_initiate_checkout_upgrade(sample_plan: Plan) -> None:
    expensive_plan = Plan(
        code="vip_monthly",
        name="VIP",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("1999.00"),
        offer_price=Decimal("1499.00"),
        max_seconds_per_request=300,
        max_usage_per_day=500,
    )
    plan_repo = InMemoryPlanRepo([sample_plan, expensive_plan])
    sub_repo = InMemorySubscriptionRepo()
    gateway = FakePaymentGateway()
    user = AuthenticatedUser(user_id="user-upgrade", email="up@test.com")

    now = datetime.now(UTC)
    current_sub = Subscription(
        user_id=user.user_id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        external_subscription_id="sub_old_pro",
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=sample_plan.offer_price,  # 599.00
        ),
    )
    await sub_repo.save(current_sub)

    uc = InitiateCheckoutUseCase(plan_repo, gateway, sub_repo)
    result = await uc.execute(user, "vip_monthly", "https://return.url")

    assert result.subscription_id == "sub_fake_vip_monthly"
    assert result.checkout_session_id == "session_fake_vip_monthly"
    # Charge collected now, no future first charge time
    assert gateway.last_first_charge_time is None
    # Checkout does not mutate subscription state; webhook processing owns updates.
    assert gateway.cancelled_ids == []
    sub_after = await sub_repo.get_latest_by_user_id(user.user_id)
    assert sub_after is not None
    assert sub_after.status == SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_initiate_checkout_same_plan_active_error(sample_plan: Plan) -> None:
    plan_repo = InMemoryPlanRepo([sample_plan])
    sub_repo = InMemorySubscriptionRepo()
    gateway = FakePaymentGateway()
    user = AuthenticatedUser(user_id="user-same", email="same@test.com")

    now = datetime.now(UTC)
    current_sub = Subscription(
        user_id=user.user_id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=sample_plan.offer_price,  # 599.00
        ),
    )
    await sub_repo.save(current_sub)

    uc = InitiateCheckoutUseCase(plan_repo, gateway, sub_repo)
    with pytest.raises(ActiveSubscriptionError):
        await uc.execute(user, "pro_monthly", "https://return.url")


@pytest.mark.asyncio
async def test_initiate_checkout_same_plan_cancelled_schedules_future(sample_plan: Plan) -> None:
    plan_repo = InMemoryPlanRepo([sample_plan])
    sub_repo = InMemorySubscriptionRepo()
    gateway = FakePaymentGateway()
    user = AuthenticatedUser(user_id="user-cancelled-same", email="same2@test.com")

    now = datetime.now(UTC)
    period_end = now + timedelta(days=15)
    current_sub = Subscription(
        user_id=user.user_id,
        status=SubscriptionStatus.CANCELLED,
        current_period_start=now - timedelta(days=15),
        current_period_end=period_end,
        cancelled_at=now - timedelta(days=2),
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=sample_plan.offer_price,  # 599.00
        ),
    )
    await sub_repo.save(current_sub)

    uc = InitiateCheckoutUseCase(plan_repo, gateway, sub_repo)
    result = await uc.execute(user, "pro_monthly", "https://return.url")

    assert result.subscription_id == "sub_fake_pro_monthly"
    assert result.checkout_session_id == "session_fake_pro_monthly"
    assert gateway.last_first_charge_time == period_end


@pytest.mark.asyncio
async def test_handle_webhook_invalid_signature() -> None:
    uc = HandleSubscriptionWebhookUseCase(
        payment_gateway=FakePaymentGateway(valid_sig=False),
        webhook_repo=InMemoryWebhookRepo(),
        subscription_repo=InMemorySubscriptionRepo(),
        plan_repo=InMemoryPlanRepo([]),
    )
    with pytest.raises(InvalidWebhookSignatureError):
        await uc.execute(b"{}", "invalid", "123", {})


@pytest.mark.asyncio
async def test_handle_webhook_activation_and_idempotency(sample_plan: Plan) -> None:
    gateway = FakePaymentGateway(valid_sig=True)
    webhook_repo = InMemoryWebhookRepo()
    sub_repo = InMemorySubscriptionRepo()
    plan_repo = InMemoryPlanRepo([sample_plan])

    uc = HandleSubscriptionWebhookUseCase(gateway, webhook_repo, sub_repo, plan_repo)

    event_payload = {
        "event_id": "evt_101",
        "type": "SUBSCRIPTION_ACTIVATION",
        "data": {
            "subscription_id": "cf_sub_999",
            "customer_id": "usr_buyer",
            "plan_id": "pro_monthly",
        },
    }

    # First delivery
    res = await uc.execute(b"{}", "valid", "123", event_payload)
    assert res is True

    # Subscription created
    created_sub = await sub_repo.get_by_external_id("cf_sub_999")
    assert created_sub is not None
    assert created_sub.status == SubscriptionStatus.ACTIVE
    assert created_sub.snapshot.plan_name == "Pro"
    assert created_sub.snapshot.max_seconds_per_request == 120

    # Duplicate delivery (idempotency test)
    res_dup = await uc.execute(b"{}", "valid", "123", event_payload)
    assert res_dup is True


@pytest.mark.asyncio
async def test_handle_webhook_downgrade_keeps_current_subscription(sample_plan: Plan) -> None:
    cheaper_plan = Plan(
        code="basic_monthly",
        name="Basic",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("499.00"),
        offer_price=Decimal("199.00"),
        max_seconds_per_request=30,
        max_usage_per_day=30,
    )
    gateway = FakePaymentGateway(valid_sig=True)
    webhook_repo = InMemoryWebhookRepo()
    sub_repo = InMemorySubscriptionRepo()
    plan_repo = InMemoryPlanRepo([sample_plan, cheaper_plan])
    now = datetime.now(UTC)
    current_sub = Subscription(
        user_id="usr_downgrade",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=10),
        current_period_end=now + timedelta(days=20),
        external_subscription_id="cf_sub_current_pro",
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=sample_plan.offer_price,
        ),
    )
    await sub_repo.save(current_sub)

    uc = HandleSubscriptionWebhookUseCase(gateway, webhook_repo, sub_repo, plan_repo)
    await uc.execute(
        b"{}",
        "valid",
        "123",
        {
            "event_id": "evt_downgrade",
            "type": "SUBSCRIPTION_ACTIVATION",
            "data": {
                "subscription_id": "cf_sub_future_basic",
                "customer_id": "usr_downgrade",
                "plan_id": "basic_monthly",
            },
        },
    )

    assert await sub_repo.get_by_external_id("cf_sub_future_basic") is None
    active_sub = await sub_repo.get_active_by_user_id("usr_downgrade")
    assert active_sub is not None
    assert active_sub.external_subscription_id == "cf_sub_current_pro"
    assert gateway.cancelled_ids == []


@pytest.mark.asyncio
async def test_handle_webhook_upgrade_stops_current_and_saves_new(sample_plan: Plan) -> None:
    expensive_plan = Plan(
        code="vip_monthly",
        name="VIP",
        billing_period=BillingPeriod.MONTHLY,
        actual_price=Decimal("1999.00"),
        offer_price=Decimal("1499.00"),
        max_seconds_per_request=300,
        max_usage_per_day=500,
    )
    gateway = FakePaymentGateway(valid_sig=True)
    webhook_repo = InMemoryWebhookRepo()
    sub_repo = InMemorySubscriptionRepo()
    plan_repo = InMemoryPlanRepo([sample_plan, expensive_plan])
    now = datetime.now(UTC)
    current_sub = Subscription(
        user_id="usr_upgrade",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        external_subscription_id="cf_sub_current_pro",
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=sample_plan.offer_price,
        ),
    )
    await sub_repo.save(current_sub)

    uc = HandleSubscriptionWebhookUseCase(gateway, webhook_repo, sub_repo, plan_repo)
    await uc.execute(
        b"{}",
        "valid",
        "123",
        {
            "event_id": "evt_upgrade",
            "type": "SUBSCRIPTION_ACTIVATION",
            "data": {
                "subscription_id": "cf_sub_new_vip",
                "customer_id": "usr_upgrade",
                "plan_id": "vip_monthly",
            },
        },
    )

    old_sub = await sub_repo.get_by_external_id("cf_sub_current_pro")
    assert old_sub is not None
    assert old_sub.status == SubscriptionStatus.CANCELLED
    assert "cf_sub_current_pro" in gateway.cancelled_ids

    new_sub = await sub_repo.get_by_external_id("cf_sub_new_vip")
    assert new_sub is not None
    assert new_sub.status == SubscriptionStatus.ACTIVE
    assert new_sub.snapshot.plan_name == "VIP"


@pytest.mark.asyncio
async def test_handle_webhook_same_active_subscription_error(sample_plan: Plan) -> None:
    gateway = FakePaymentGateway(valid_sig=True)
    webhook_repo = InMemoryWebhookRepo()
    sub_repo = InMemorySubscriptionRepo()
    plan_repo = InMemoryPlanRepo([sample_plan])
    now = datetime.now(UTC)
    current_sub = Subscription(
        user_id="usr_same",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=25),
        external_subscription_id="cf_sub_current_pro",
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=sample_plan.offer_price,
        ),
    )
    await sub_repo.save(current_sub)

    uc = HandleSubscriptionWebhookUseCase(gateway, webhook_repo, sub_repo, plan_repo)
    with pytest.raises(ActiveSubscriptionError):
        await uc.execute(
            b"{}",
            "valid",
            "123",
            {
                "event_id": "evt_same_active",
                "type": "SUBSCRIPTION_ACTIVATION",
                "data": {
                    "subscription_id": "cf_sub_duplicate_pro",
                    "customer_id": "usr_same",
                    "plan_id": "pro_monthly",
                },
            },
        )


@pytest.mark.asyncio
async def test_handle_webhook_same_cancelled_keeps_current_until_period_end(
    sample_plan: Plan,
) -> None:
    gateway = FakePaymentGateway(valid_sig=True)
    webhook_repo = InMemoryWebhookRepo()
    sub_repo = InMemorySubscriptionRepo()
    plan_repo = InMemoryPlanRepo([sample_plan])
    now = datetime.now(UTC)
    current_sub = Subscription(
        user_id="usr_same_cancelled",
        status=SubscriptionStatus.CANCELLED,
        current_period_start=now - timedelta(days=15),
        current_period_end=now + timedelta(days=15),
        cancelled_at=now - timedelta(days=2),
        external_subscription_id="cf_sub_cancelled_pro",
        snapshot=PlanSnapshot(
            plan_name="Pro",
            max_seconds_per_request=120,
            max_usage_per_day=150,
            price=sample_plan.offer_price,
        ),
    )
    await sub_repo.save(current_sub)

    uc = HandleSubscriptionWebhookUseCase(gateway, webhook_repo, sub_repo, plan_repo)
    await uc.execute(
        b"{}",
        "valid",
        "123",
        {
            "event_id": "evt_same_cancelled",
            "type": "SUBSCRIPTION_ACTIVATION",
            "data": {
                "subscription_id": "cf_sub_future_pro",
                "customer_id": "usr_same_cancelled",
                "plan_id": "pro_monthly",
            },
        },
    )

    assert await sub_repo.get_by_external_id("cf_sub_future_pro") is None
    existing_sub = await sub_repo.get_by_external_id("cf_sub_cancelled_pro")
    assert existing_sub is not None
    assert existing_sub.status == SubscriptionStatus.CANCELLED
    assert gateway.cancelled_ids == []


@pytest.mark.asyncio
async def test_check_entitlement_duration_and_daily_quota(sample_plan: Plan) -> None:
    sub_repo = InMemorySubscriptionRepo()
    usage_tracker = InMemoryUsageTracker(initial_usage=9)
    settings = Settings(free_tier_max_seconds=10, free_tier_max_requests_per_day=10)

    checker = CheckEntitlementUseCase(sub_repo, usage_tracker, settings)

    # 1. Audio too long
    with pytest.raises(AudioExceedsTierLimitError):
        await checker.execute("user-1", audio_duration_seconds=15.0)

    # 2. Audio ok, usage 9/10 (succeeds)
    balance = await checker.execute("user-1", audio_duration_seconds=8.0)
    assert balance.used_today == 9
    assert balance.remaining == 1

    # Record usage
    updated = await checker.record_usage("user-1")
    assert updated == 10

    # 3. Quota exhausted (10/10)
    with pytest.raises(DailyQuotaExceededError):
        await checker.execute("user-1", audio_duration_seconds=5.0)
