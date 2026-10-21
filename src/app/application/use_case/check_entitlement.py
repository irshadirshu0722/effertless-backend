"""Use case for verifying user tier limits and daily usage entitlements."""

from app.core.config import Settings
from app.core.exceptions import AudioExceedsTierLimitError, DailyQuotaExceededError
from app.domain.value_objects.plan_snapshot import TierLimits
from app.domain.value_objects.usage_balance import UsageBalance
from app.ports.repository import SubscriptionRepository


class CheckEntitlementUseCase:
    """Verifies that a user has sufficient quota and complies with duration limits."""

    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        settings: Settings,
    ) -> None:
        self._subscription_repo = subscription_repo
        self._usage_tracker = None
        self._settings = settings

    async def get_applicable_limits(self, user_id: str) -> TierLimits:
        """Resolve current limits from active subscription or default free tier."""
        sub = await self._subscription_repo.get_active_by_user_id(user_id)
        if sub and sub.is_currently_active():
            return sub.limits

        return TierLimits(
            max_seconds_per_request=self._settings.free_tier_max_seconds,
            max_usage_per_day=self._settings.free_tier_max_requests_per_day,
        )

    async def execute(
        self,
        user_id: str,
        audio_duration_seconds: float = 0.0,
    ) -> UsageBalance:
        limits = await self.get_applicable_limits(user_id)

        # Duration validation
        if audio_duration_seconds > 0 and audio_duration_seconds > limits.max_seconds_per_request:
            raise AudioExceedsTierLimitError(
                requested_seconds=audio_duration_seconds,
                max_seconds=limits.max_seconds_per_request,
            )

        # Daily usage validation
        used_today = await self._usage_tracker.get_today_usage(user_id)
        if used_today >= limits.max_usage_per_day:
            raise DailyQuotaExceededError(daily_limit=limits.max_usage_per_day)

        return UsageBalance(used_today=used_today, limit=limits.max_usage_per_day)

    async def record_usage(self, user_id: str) -> int:
        """Increment daily consumption after successful operation."""
        return await self._usage_tracker.increment_today_usage(user_id)
