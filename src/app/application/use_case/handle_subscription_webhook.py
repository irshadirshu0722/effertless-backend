"""Use case for processing Cashfree subscription webhook events idempotently."""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.exceptions import InvalidWebhookSignatureError, PlanNotFoundError
from app.domain.entities.subscription import Subscription, SubscriptionStatus
from app.domain.value_objects.plan_snapshot import PlanSnapshot
from app.ports.subscription import (
    PaymentGateway,
    PlanRepository,
    SubscriptionRepository,
    WebhookEventRepository,
)


class HandleSubscriptionWebhookUseCase:
    """Processes subscription lifecycle webhooks idempotently."""

    def __init__(
        self,
        payment_gateway: PaymentGateway,
        webhook_repo: WebhookEventRepository,
        subscription_repo: SubscriptionRepository,
        plan_repo: PlanRepository,
    ) -> None:
        self._payment_gateway = payment_gateway
        self._webhook_repo = webhook_repo
        self._subscription_repo = subscription_repo
        self._plan_repo = plan_repo

    async def execute(
        self,
        raw_payload: bytes,
        signature: str,
        timestamp: str,
        event_data: dict[str, Any],
    ) -> bool:
        # Step 1: Cryptographic signature verification
        if not self._payment_gateway.verify_webhook_signature(raw_payload, signature, timestamp):
            raise InvalidWebhookSignatureError()

        # Step 2: Extract event identity
        event_type = str(
            event_data.get("type")
            or event_data.get("event")
            or event_data.get("event_type")
            or "UNKNOWN"
        )
        data = event_data.get("data") or event_data.get("subscription") or event_data
        event_id = str(
            event_data.get("event_id")
            or event_data.get("id")
            or f"{event_type}_{data.get('subscription_id')}_{timestamp}"
        )

        # Step 3: Check idempotency
        if await self._webhook_repo.has_been_processed(event_id):
            return True

        # Step 4: Process event
        now = datetime.now(UTC)
        normalized_type = event_type.upper()

        if any(term in normalized_type for term in ("ACTIVATION", "CHARGED", "NEW", "SUCCESS")):
            sub_id = str(data.get("subscription_id") or "")
            customer_id = str(
                data.get("customer_id") or data.get("customer_details", {}).get("customer_id") or ""
            )
            plan_code = str(
                data.get("plan_id") or data.get("plan_details", {}).get("plan_id") or ""
            )

            plan = await self._plan_repo.get_by_code(plan_code)
            if not plan:
                raise PlanNotFoundError(plan_code)

            # Freeze plan terms into immutable snapshot
            snapshot = PlanSnapshot(
                plan_name=plan.name,
                max_seconds_per_request=plan.max_seconds_per_request,
                max_usage_per_day=plan.max_usage_per_day,
                price=plan.offer_price,
                currency=plan.currency,
            )

            # Duration calculation (30 days default for monthly, 7 for weekly)
            duration_days = 7 if plan.billing_period.lower() == "weekly" else 30
            period_end = now + timedelta(days=duration_days)

            # Existing subscription or new
            existing_sub = await self._subscription_repo.get_by_external_id(sub_id)
            subscription = Subscription(
                id=existing_sub.id if existing_sub else None,  # type: ignore[arg-type]
                user_id=customer_id or (existing_sub.user_id if existing_sub else "unknown"),
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                provider="cashfree",
                external_subscription_id=sub_id,
                external_customer_id=customer_id,
                current_period_start=now,
                current_period_end=period_end,
                snapshot=snapshot,
            )
            await self._subscription_repo.save(subscription)

        elif any(term in normalized_type for term in ("CANCEL", "EXPIRED", "PAUSED")):
            sub_id = str(data.get("subscription_id") or "")
            existing_sub = await self._subscription_repo.get_by_external_id(sub_id)
            if existing_sub:
                status = (
                    SubscriptionStatus.CANCELLED
                    if "CANCEL" in normalized_type
                    else SubscriptionStatus.EXPIRED
                )
                updated_sub = Subscription(
                    id=existing_sub.id,
                    user_id=existing_sub.user_id,
                    plan_id=existing_sub.plan_id,
                    status=status,
                    provider=existing_sub.provider,
                    external_subscription_id=existing_sub.external_subscription_id,
                    external_customer_id=existing_sub.external_customer_id,
                    current_period_start=existing_sub.current_period_start,
                    current_period_end=existing_sub.current_period_end,
                    cancelled_at=now,
                    snapshot=existing_sub.snapshot,
                )
                await self._subscription_repo.save(updated_sub)

        # Step 5: Record event for idempotency
        await self._webhook_repo.record_event(
            event_id=event_id,
            event_type=event_type,
            payload=event_data,
            status="processed",
        )
        return True
