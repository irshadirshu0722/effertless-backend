"""Use case for fetching current user subscription status and quota balance."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.value_objects.plan_snapshot import TierLimits
from app.domain.value_objects.usage_balance import UsageBalance
from app.ports.subscription import SubscriptionRepository, UsageTracker


@dataclass(frozen=True, slots=True)
class UserSubscriptionDetails:
    """User subscription status, tier limits, and current quota consumption."""

    status: str
    plan_name: str
    current_period_end: datetime | None
    limits: TierLimits
    usage_today: UsageBalance


class GetUserSubscriptionUseCase:
    """Queries user subscription or falls back to free trial defaults."""

    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        usage_tracker: UsageTracker,
        settings: Settings,
    ) -> None:
        self._subscription_repo = subscription_repo
        self._usage_tracker = usage_tracker
        self._settings = settings

    async def execute(self, user_id: str) -> UserSubscriptionDetails:
        active_sub = await self._subscription_repo.get_active_by_user_id(user_id)
        used_today = await self._usage_tracker.get_today_usage(user_id)

        if active_sub and active_sub.is_currently_active():
            return UserSubscriptionDetails(
                status=active_sub.status.value,
                plan_name=active_sub.snapshot.plan_name,
                current_period_end=active_sub.current_period_end,
                limits=active_sub.limits,
                usage_today=UsageBalance(
                    used_today=used_today,
                    limit=active_sub.limits.max_usage_per_day,
                ),
            )

        # Default Free Tier
        free_limits = TierLimits(
            max_seconds_per_request=self._settings.free_tier_max_seconds,
            max_usage_per_day=self._settings.free_tier_max_requests_per_day,
        )
        now = datetime.now(UTC)
        trial_end = now + timedelta(days=self._settings.free_tier_days)

        return UserSubscriptionDetails(
            status=SubscriptionStatus.TRIALING.value,
            plan_name="Free",
            current_period_end=trial_end,
            limits=free_limits,
            usage_today=UsageBalance(
                used_today=used_today,
                limit=free_limits.max_usage_per_day,
            ),
        )
