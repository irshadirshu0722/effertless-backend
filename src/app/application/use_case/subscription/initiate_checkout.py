"""Use case for creating a Cashfree checkout subscription session."""

from datetime import UTC, datetime, timedelta

from app.application.use_case.subscription import CheckoutSessionResult, PlanNotFoundError
from app.application.use_case.subscription.command import InitiateCheckoutCommand
from app.core.exceptions import ActiveSubscriptionError
from app.domain.entities.plan import BillingPeriod, Plan
from app.domain.entities.subscription import (
    Subscription,
    SubscriptionOperationType,
    SubscriptionStatus,
)
from app.domain.value_objects.plan_snapshot import PlanSnapshot
from app.ports.repository import PlanRepository, SubscriptionRepository
from app.ports.services import PaymentGateway


class InitiateCheckoutUseCase:
    def __init__(
        self,
        plan_repo: PlanRepository,
        payment_gateway: PaymentGateway,
        subscription_repo: SubscriptionRepository | None = None,
    ) -> None:
        self._plan_repo = plan_repo
        self._payment_gateway = payment_gateway
        self._subscription_repo = subscription_repo

    @staticmethod
    def _snapshot_for(plan: Plan) -> PlanSnapshot:
        return PlanSnapshot(
            plan_name=plan.name,
            max_seconds_per_request=plan.max_seconds_per_request,
            max_usage_per_day=plan.max_usage_per_day,
            price=plan.offer_price,
            currency=plan.currency,
        )

    async def execute(self, cm: InitiateCheckoutCommand) -> CheckoutSessionResult:
        plan = await self._plan_repo.get_by_code(cm.plan_code)
        if not plan or not plan.is_active or plan.is_deleted:
            raise PlanNotFoundError(cm.plan_code)

        now = datetime.now(UTC)
        current_sub = await self._subscription_repo.get_active_by_user_id(cm.user.user_id)
        operation_type = SubscriptionOperationType.NEW
        first_charge_time: datetime | None = None
        if current_sub is not None:
            period_end = (
                current_sub.current_period_end
                if current_sub.current_period_end.tzinfo is not None
                else current_sub.current_period_end.replace(tzinfo=UTC)
            )

            if period_end > now:
                current_price = current_sub.snapshot.price
                new_price = plan.offer_price

                if new_price < current_price:
                    # Downgrade: schedule the new subscription after the
                    # current billing period.
                    operation_type = SubscriptionOperationType.DOWNGRADE
                    first_charge_time = period_end

                elif new_price > current_price:
                    operation_type = SubscriptionOperationType.UPGRADE
                    # Upgrade: initiate the new subscription now.
                    first_charge_time = None

                else:
                    # Same price: check whether the user has an active subscription
                    # to the same plan.
                    is_active_and_not_cancelled = (
                        current_sub.status == SubscriptionStatus.ACTIVE
                        and current_sub.cancelled_at is None
                    )

                    is_same_plan = current_sub.plan_id == plan.id

                    if is_active_and_not_cancelled and is_same_plan:
                        raise ActiveSubscriptionError(
                            "You already have an active subscription to this plan."
                        )
                    operation_type = SubscriptionOperationType.RENEWAL
                    # Same price, different plan, or cancelled subscription:
                    # allow checkout to proceed.
                    first_charge_time = period_end

        subscription_id, checkout_session_id = await self._payment_gateway.create_checkout_session(
            user_id=cm.user.user_id,
            user_email=cm.user.email,
            plan=plan,
            return_url=cm.return_url,
            first_charge_time=first_charge_time,
        )

        period_start = first_charge_time or now
        period = BillingPeriod.from_str(plan.billing_period)
        period_end = period_start + timedelta(days=period.duration_days)

        pending_subscription = Subscription(
            id=None,
            user_id=cm.user.user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.PENDING,
            provider="cashfree",
            external_subscription_id=subscription_id,
            external_customer_id=None,
            current_period_start=period_start,
            current_period_end=period_end,
            snapshot=self._snapshot_for(plan),
            created_at=now,
            updated_at=now,
            operation_type=operation_type,
            related_subscription_id=current_sub.id if current_sub else None,
        )

        await self._subscription_repo.save(pending_subscription)

        return CheckoutSessionResult(
            subscription_id=subscription_id,
            checkout_session_id=checkout_session_id,
            status="pending",
        )
