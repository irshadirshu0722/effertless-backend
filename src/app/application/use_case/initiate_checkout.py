"""Use case for creating a Cashfree checkout subscription session."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.exceptions import ActiveSubscriptionError, PlanNotFoundError
from app.domain.entities.authenticated_user import AuthenticatedUser
from app.domain.entities.plan import BillingPeriod, Plan
from app.domain.entities.subscription import Subscription, SubscriptionStatus
from app.domain.value_objects.plan_snapshot import PlanSnapshot
from app.ports.subscription import PaymentGateway, PlanRepository, SubscriptionRepository


@dataclass(frozen=True, slots=True)
class CheckoutSessionResult:
    subscription_id: str
    checkout_session_id: str
    status: str = "pending"


class InitiateCheckoutUseCase:
    """Creates a subscription checkout session via the payment gateway."""

    def __init__(
        self,
        plan_repo: PlanRepository,
        payment_gateway: PaymentGateway,
        subscription_repo: SubscriptionRepository | None = None,
    ) -> None:
        self._plan_repo = plan_repo
        self._payment_gateway = payment_gateway
        self._subscription_repo = subscription_repo

    async def _get_current_subscription(self, user_id: str) -> Subscription | None:
        if self._subscription_repo is None:
            return None

        # Check for active subscription first
        active_sub = await self._subscription_repo.get_active_by_user_id(user_id)
        if active_sub:
            return active_sub
        return None

    @staticmethod
    def _snapshot_for(plan: Plan) -> PlanSnapshot:
        return PlanSnapshot(
            plan_name=plan.name,
            max_seconds_per_request=plan.max_seconds_per_request,
            max_usage_per_day=plan.max_usage_per_day,
            price=plan.offer_price,
            currency=plan.currency,
        )

    async def execute(
        self,
        user: AuthenticatedUser,
        plan_code: str,
        return_url: str,
    ) -> CheckoutSessionResult:
        plan = await self._plan_repo.get_by_code(plan_code)
        if not plan or not plan.is_active or plan.is_deleted:
            raise PlanNotFoundError(plan_code)

        now = datetime.now(UTC)
        current_sub = await self._get_current_subscription(user.user_id)

        first_charge_time: datetime | None = None
        if current_sub is not None:
            period_end = (
                current_sub.current_period_end
                if current_sub.current_period_end.tzinfo is not None
                else current_sub.current_period_end.replace(tzinfo=UTC)
            )

            if period_end > now and current_sub.status != SubscriptionStatus.EXPIRED:
                current_price = current_sub.snapshot.price
                new_price = plan.offer_price

                if new_price < current_price:
                    # Downgrade: schedule the new subscription after the
                    # current billing period.
                    first_charge_time = period_end

                elif new_price > current_price:
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

                    # Same price, different plan, or cancelled subscription:
                    # allow checkout to proceed.
                    first_charge_time = period_end

        # Create the Cashfree checkout session.
        subscription_id, checkout_session_id = await self._payment_gateway.create_checkout_session(
            user_id=user.user_id,
            user_email=user.email,
            plan=plan,
            return_url=return_url,
            first_charge_time=first_charge_time,
        )

        period_start = first_charge_time or now
        period = BillingPeriod.from_str(plan.billing_period)
        period_end = period_start + timedelta(days=period.duration_days)

        pending_subscription = Subscription(
            id=None,
            user_id=user.user_id,
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
        )

        await self._subscription_repo.save(pending_subscription)

        return CheckoutSessionResult(
            subscription_id=subscription_id,
            checkout_session_id=checkout_session_id,
            status="pending",
        )
