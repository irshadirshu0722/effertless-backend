"""Use case for creating a Cashfree checkout subscription session."""

from datetime import UTC, datetime, timedelta

from app.application.use_case.subscription import PlanNotFoundError
from app.application.use_case.subscription.command import InitiateCheckoutCommand
from app.application.use_case.subscription.exceptions import TrailPlanNotFoundError
from app.application.use_case.subscription.results import CheckoutSessionResult
from app.core.config import settings
from app.core.exceptions import ActiveSubscriptionError
from app.domain.entities.plan import Plan, PlanCode
from app.domain.entities.subscription import (
    Subscription,
    SubscriptionOperationType,
    SubscriptionStatus,
)
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
    def _find_operation_type(
        current_name: str,
        new: Plan,
    ) -> SubscriptionOperationType:
        current_code = PlanCode(current_name.strip().upper())
        new_code = PlanCode(new.code.strip().upper())

        if current_code == new_code:
            return SubscriptionOperationType.RENEWAL

        plan_order = {
            PlanCode.BASIC: 1,
            PlanCode.STANDARD: 2,
            PlanCode.PRO: 3,
        }

        if current_code not in plan_order or new_code not in plan_order:
            raise ValueError("Invalid current or new subscription plan")

        if plan_order[new_code] > plan_order[current_code]:
            return SubscriptionOperationType.UPGRADE

        return SubscriptionOperationType.DOWNGRADE

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
                operation_type = self._find_operation_type(
                    current_sub.snapshot_plan_name,
                    plan,
                )

                if operation_type != SubscriptionOperationType.RENEWAL:
                    if not cm.replace:
                        first_charge_time = period_end
                else:
                    if current_sub.is_active:
                        raise ActiveSubscriptionError(
                            "You already have an active subscription to this plan."
                        )

                    first_charge_time = period_end

        has_trial = False
        trial_start = None
        trial_end = None

        if current_sub is None:
            has_used_trial = await self._subscription_repo.has_user_used_trial(
                user_id=cm.user.user_id
            )

            if not has_used_trial:
                trail_plan = await self._plan_repo.get_by_code(PlanCode.TRAIL)

                if not trail_plan or not trail_plan.is_active or trail_plan.is_deleted:
                    raise TrailPlanNotFoundError()

                has_trial = True
                trial_start = now
                trial_end = now + timedelta(days=settings.free_tier_days)
                first_charge_time = trial_end

        subscription_id, checkout_session_id = await self._payment_gateway.create_checkout_session(
            user_id=cm.user.user_id,
            user_email=cm.user.email,
            plan=plan,
            return_url=cm.return_url,
            first_charge_time=first_charge_time,
        )

        period_start = first_charge_time or now
        period_end = period_start + timedelta(days=Subscription.get_total_days())

        pending_subscription = Subscription(
            user_id=cm.user.user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.PENDING,
            provider="cashfree",
            external_subscription_id=subscription_id,
            external_customer_id=None,
            current_period_start=period_start,
            current_period_end=period_end,
            created_at=now,
            updated_at=now,
            operation_type=operation_type,
            related_subscription_id=(current_sub.id if current_sub is not None else None),
            has_trial=has_trial,
            trial_start=trial_start,
            trial_end=trial_end,
            snapshot_currency=plan.currency,
            snapshot_max_seconds=plan.monthly_seconds,
            snapshot_plan_name=plan.name,
            snapshot_price=plan.offer_price,
        )

        await self._subscription_repo.save(pending_subscription)

        return CheckoutSessionResult(
            subscription_id=subscription_id,
            checkout_session_id=checkout_session_id,
            status="pending",
        )
