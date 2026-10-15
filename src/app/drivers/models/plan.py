"""Process Cashfree subscription status-change webhooks."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import (
    InvalidWebhookSignatureError,
    SubscriptionPaymentError,
)
from app.domain.entities.subscription import (
    Subscription,
    SubscriptionStatus,
)
from app.ports.subscription import (
    PaymentGateway,
    PlanRepository,
    SubscriptionRepository,
    WebhookEventRepository,
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

    async def _get_previous_subscription(
        self,
        incoming: Subscription,
    ) -> Subscription | None:
        """Find the previous eligible subscription, excluding incoming."""

        current = await self._subscription_repo.get_active_by_user_id(incoming.user_id)

        if current is None:
            return None

        if current.id == incoming.id:
            return None

        if current.external_subscription_id == incoming.external_subscription_id:
            return None

        return current

    async def _save_status(
        self,
        subscription: Subscription,
        status: SubscriptionStatus,
        now: datetime,
    ) -> Subscription:
        """Persist status while retaining the billing dates."""

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
            external_subscription_id=(subscription.external_subscription_id),
            external_customer_id=subscription.external_customer_id,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancelled_at=cancelled_at,
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
        self,
        current: Subscription,
        now: datetime,
    ) -> None:
        """Cancel a live previous subscription in Cashfree and the DB."""

        if current.status == SubscriptionStatus.CANCELLED:
            request_logger.info(
                "Previous subscription is already cancelled: subscription_id=%s",
                current.external_subscription_id,
            )
            return

        if current.status not in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        }:
            raise ValueError(f"Cannot replace a previous subscription with status {current.status}")

        if current.external_subscription_id:
            cancelled = await self._payment_gateway.cancel_subscription(
                current.external_subscription_id
            )

            if not cancelled:
                request_logger.error(
                    "Could not cancel previous subscription in Cashfree: subscription_id=%s",
                    current.external_subscription_id,
                )
                raise SubscriptionPaymentError(
                    "Failed to cancel previous subscription in Cashfree: "
                    f"{current.external_subscription_id}"
                )

        # Update the local record only after the provider accepts
        # the cancellation request.
        await self._save_status(
            current,
            SubscriptionStatus.CANCELLED,
            now,
        )

    async def _activate_or_keep_pending(
        self,
        incoming: Subscription,
        now: datetime,
    ) -> None:
        """Activate a due subscription or leave a future one pending."""

        scheduled_start = self._as_utc(incoming.current_period_start)

        if scheduled_start > now:
            request_logger.info(
                "Subscription remains pending until scheduled start: "
                "subscription_id=%s scheduled_start=%s",
                incoming.external_subscription_id,
                scheduled_start,
            )
            return

        if incoming.status != SubscriptionStatus.ACTIVE:
            await self._save_status(
                incoming,
                SubscriptionStatus.ACTIVE,
                now,
            )

    async def _handle_status_changed(
        self,
        data: dict[str, Any],
        subscription_details: dict[str, Any],
        now: datetime,
    ) -> None:
        """Handle scheduled changes, activation, renewal and cancellation."""

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

        # A scheduled subscription is not yet the active plan.
        # Do not cancel the user's existing subscription here.
        if provider_status == "SCHEDULED":
            request_logger.info(
                "Incoming subscription is scheduled; retaining current "
                "subscription: subscription_id=%s",
                incoming.external_subscription_id,
            )
            return

        # Handle cancellation of the incoming subscription only.
        # A still-valid previous subscription should remain untouched.
        if provider_status in {"CANCELLED", "CANCELED"}:
            if incoming.status != SubscriptionStatus.CANCELLED:
                await self._save_status(
                    incoming,
                    SubscriptionStatus.CANCELLED,
                    now,
                )
            return

        if provider_status == "EXPIRED":
            if incoming.status != SubscriptionStatus.EXPIRED:
                await self._save_status(
                    incoming,
                    SubscriptionStatus.EXPIRED,
                    now,
                )
            return

        if provider_status == "PAUSED":
            request_logger.info(
                "Subscription paused; explicit local pause handling "
                "is not configured: subscription_id=%s",
                incoming.external_subscription_id,
            )
            return

        # A failed payment is not necessarily a permanently cancelled
        # subscription. Handle payment failures and retries through the
        # appropriate payment-event workflow.
        if provider_status in {"FAILED", "PAYMENT_FAILED"}:
            request_logger.warning(
                "Subscription/payment failure requires payment handling: subscription_id=%s",
                incoming.external_subscription_id,
            )
            return

        if provider_status != "ACTIVE":
            request_logger.info(
                "Ignoring unsupported subscription status: %s",
                provider_status,
            )
            return

        # Ignore duplicate ACTIVE notifications.
        if incoming.status == SubscriptionStatus.ACTIVE:
            return

        if incoming.status != SubscriptionStatus.PENDING:
            request_logger.info(
                "Ignoring ACTIVE event for non-pending subscription: "
                "subscription_id=%s local_status=%s",
                incoming.external_subscription_id,
                incoming.status,
            )
            return

        scheduled_start = self._as_utc(incoming.current_period_start)

        # Critical: a future-dated incoming subscription must not cause
        # the currently active subscription to be cancelled.
        if scheduled_start > now:
            request_logger.info(
                "Incoming subscription has a future start; keeping it "
                "pending and retaining the current subscription: "
                "subscription_id=%s scheduled_start=%s",
                incoming.external_subscription_id,
                scheduled_start,
            )
            return

        current = await self._get_previous_subscription(incoming)

        # No previous eligible subscription.
        if current is None:
            await self._activate_or_keep_pending(incoming, now)
            return

        current_price = current.snapshot.price
        incoming_price = incoming.snapshot.price

        request_logger.info(
            "Comparing subscriptions: user_id=%s current_plan=%s "
            "incoming_plan=%s current_price=%s incoming_price=%s",
            incoming.user_id,
            current.plan_id,
            incoming.plan_id,
            current_price,
            incoming_price,
        )

        # UPGRADE: retire the old subscription only when the new
        # subscription is due to take over.
        if incoming_price > current_price:
            await self._cancel_previous_subscription(current, now)
            await self._activate_or_keep_pending(incoming, now)
            return

        # DOWNGRADE: the SCHEDULED or future-start path above returns
        # without cancelling the current subscription. Once the new
        # subscription is ACTIVE and due, replace the old one.
        if incoming_price < current_price:
            await self._cancel_previous_subscription(current, now)
            await self._activate_or_keep_pending(incoming, now)
            return

        # Equal prices alone do not establish a renewal.
        if incoming.plan_id != current.plan_id:
            raise ValueError(
                "Cannot classify equal-price, different-plan subscriptions as a renewal"
            )

        # RENEWAL: do not cancel the previous subscription.
        await self._activate_or_keep_pending(incoming, now)

        request_logger.info(
            "Renewal processed without cancelling previous subscription: "
            "user_id=%s incoming_subscription_id=%s",
            incoming.user_id,
            incoming.external_subscription_id,
        )

    async def execute(
        self,
        raw_payload: bytes,
        signature: str,
        timestamp: str,
        event_data: dict[str, Any],
    ) -> bool:
        """Verify and process subscription status-change webhooks."""

        if not self._payment_gateway.verify_webhook_signature(
            raw_payload,
            signature,
            timestamp,
        ):
            raise InvalidWebhookSignatureError()

        event_type, data, subscription_details = self._extract_data(event_data)

        if event_type != "SUBSCRIPTION_STATUS_CHANGED":
            request_logger.info(
                "Ignoring unsupported webhook event: %s",
                event_type,
            )
            return True

        subscription_id = str(
            subscription_details.get("subscription_id") or data.get("subscription_id") or ""
        )

        event_time = str(event_data.get("event_time") or timestamp)

        event_id = str(
            event_data.get("event_id")
            or event_data.get("id")
            or f"{event_type}_{subscription_id}_{event_time}"
        )

        if await self._webhook_repo.has_been_processed(event_id):
            request_logger.info(
                "Duplicate webhook ignored: event_id=%s",
                event_id,
            )
            return True

        now = datetime.now(UTC)

        await self._handle_status_changed(
            data,
            subscription_details,
            now,
        )

        # Persist the event only after successful processing.
        # The subscription updates and event record should share
        # one DB transaction wherever possible.
        await self._webhook_repo.record_event(
            event_id=event_id,
            event_type=event_type,
            payload=event_data,
            status="processed",
        )

        return True
