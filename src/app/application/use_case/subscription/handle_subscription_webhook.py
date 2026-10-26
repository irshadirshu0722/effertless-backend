"""Process Cashfree subscription status-change webhooks."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.application.use_case.subscription.command import SubscriptionWebhookCommand
from app.core.exceptions import InvalidWebhookSignatureError
from app.domain.entities.subscription import (
    Subscription,
    SubscriptionStatus,
)
from app.ports.repository import (
    PlanRepository,
    SubscriptionRepository,
    WebhookEventRepository,
)
from app.ports.services import (
    PaymentGateway,
)

request_logger = logging.getLogger("app.requests")


class HandleSubscriptionWebhookUseCase:
    """Process Cashfree subscription status changes idempotently."""

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

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _extract_data(
        event_data: dict[str, Any],
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        event_type = str(
            event_data.get("type")
            or event_data.get("event")
            or event_data.get("event_type")
            or "UNKNOWN"
        ).upper()

        data = event_data.get("data") or {}
        if not isinstance(data, dict):
            raise ValueError("Invalid Cashfree webhook data")

        subscription_details = data.get("subscription_details") or {}
        if not isinstance(subscription_details, dict):
            subscription_details = {}

        customer_details = data.get("customer_details") or {}
        if not isinstance(customer_details, dict):
            customer_details = {}

        plan_details = data.get("plan_details") or {}
        if not isinstance(plan_details, dict):
            plan_details = {}

        normalized_data = {
            **data,
            **{key: value for key, value in subscription_details.items() if value is not None},
            "customer_details": customer_details,
            "plan_details": plan_details,
        }

        return event_type, normalized_data, subscription_details

    async def _find_subscription(
        self,
        subscription_id: str,
        cf_subscription_id: str,
    ) -> Subscription | None:
        subscription = None

        if subscription_id:
            subscription = await self._subscription_repo.get_by_external_id(subscription_id)

        if subscription is None and cf_subscription_id:
            subscription = await self._subscription_repo.get_by_external_id(cf_subscription_id)

        return subscription

    async def _save_status(
        self,
        subscription: Subscription,
        status: SubscriptionStatus,
        now: datetime,
    ) -> Subscription:
        """Persist status while retaining the billing dates."""
        has_period_remaining = subscription.current_period_end > now
        is_active = status == SubscriptionStatus.ACTIVE or (
            status == SubscriptionStatus.CANCELLED and has_period_remaining
        )
        request_logger.info("active %s", is_active)
        if status == SubscriptionStatus.ACTIVE:
            cancelled_at = None
        elif status in {
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.EXPIRED,
        }:
            cancelled_at = subscription.cancelled_at or now
        else:
            cancelled_at = subscription.cancelled_at

        updated = Subscription(
            id=subscription.id,
            user_id=subscription.user_id,
            plan_id=subscription.plan_id,
            status=status,
            provider=subscription.provider,
            external_subscription_id=subscription.external_subscription_id,
            external_customer_id=subscription.external_customer_id,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancelled_at=cancelled_at,
            is_active=is_active,
            operation_type=subscription.operation_type,
            related_subscription_id=subscription.related_subscription_id,
            snapshot=subscription.snapshot,
            created_at=subscription.created_at,
            updated_at=now,
        )

        await self._subscription_repo.save(updated)

        request_logger.info(
            "Subscription status updated: user_id=%s subscription_id=%s status=%s",
            updated.user_id,
            updated.external_subscription_id,
            updated.status,
        )

        return updated

    async def _cancel_previous_subscription(
        self, current: Subscription, now: datetime, force_deactivate: bool = False
    ) -> None:
        """Cancel a previous subscription if it is still live."""

        if current.status in {
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.EXPIRED,
        }:
            return

        if current.external_subscription_id:
            await self._payment_gateway.cancel_subscription(current.external_subscription_id)

        await self._save_status(current, SubscriptionStatus.CANCELLED, now, force_deactivate)

    async def _handle_status_changed(
        self,
        data: dict[str, Any],
        subscription_details: dict[str, Any],
        now: datetime,
    ) -> None:
        subscription_id = str(
            subscription_details.get("subscription_id") or data.get("subscription_id") or ""
        )

        cf_subscription_id = str(subscription_details.get("cf_subscription_id") or "")

        provider_status = str(
            subscription_details.get("subscription_status") or data.get("subscription_status") or ""
        ).upper()

        if not subscription_id and not cf_subscription_id:
            raise ValueError("Cashfree webhook is missing subscription identifiers")

        incoming = await self._find_subscription(
            subscription_id,
            cf_subscription_id,
        )

        if incoming is None:
            raise ValueError(
                "No local subscription found for Cashfree subscription "
                f"{subscription_id or cf_subscription_id}"
            )

        request_logger.info(
            "Processing subscription status change: user_id=%s "
            "subscription_id=%s local_status=%s provider_status=%s",
            incoming.user_id,
            incoming.external_subscription_id,
            incoming.status,
            provider_status,
        )

        request_logger.info("Subscription operation type: %s", incoming.operation_type.value)
        try:
            new_status = SubscriptionStatus(provider_status)
        except ValueError:
            request_logger.warning(
                "Unsupported Cashfree subscription status: subscription_id=%s provider_status=%s",
                incoming.external_subscription_id,
                provider_status,
            )
            return
        if new_status == SubscriptionStatus.ACTIVE:
            related: Subscription | None = None
            related_id = incoming.related_subscription_id
            if related_id:
                related = await self._subscription_repo.get_by_id(related_id)
        await self._save_status(incoming, new_status, now)

        if related is not None:
            await self._cancel_previous_subscription(related, now)

    async def execute(self, cm: SubscriptionWebhookCommand) -> bool:
        """Verify and process only SUBSCRIPTION_STATUS_CHANGED events."""
        raw_payload, signature, timestamp, event_data = (
            cm.raw_payload,
            cm.signature,
            cm.timestamp,
            cm.event_data,
        )
        if not self._payment_gateway.verify_webhook_signature(
            raw_payload,
            signature,
            timestamp,
        ):
            raise InvalidWebhookSignatureError()

        event_type, data, subscription_details = self._extract_data(event_data)

        subscription_id = str(
            subscription_details.get("subscription_id") or data.get("subscription_id") or ""
        )

        event_time = str(event_data.get("event_time") or timestamp)

        event_id = str(
            event_data.get("event_id")
            or event_data.get("id")
            or (f"{event_type}_{subscription_id}_{event_time}")
        )

        if await self._webhook_repo.has_been_processed(event_id):
            request_logger.info(
                "Duplicate webhook ignored: event_id=%s",
                event_id,
            )
            return True
        if event_type != "SUBSCRIPTION_STATUS_CHANGED":
            request_logger.info(
                "Ignoring unsupported webhook event type: %s",
                event_type,
            )
            return True
        now = datetime.now(UTC)

        await self._handle_status_changed(
            data,
            subscription_details,
            now,
        )

        await self._webhook_repo.record_event(
            event_id=event_id,
            event_type=event_type,
            payload=event_data,
            status="processed",
        )

        return True
