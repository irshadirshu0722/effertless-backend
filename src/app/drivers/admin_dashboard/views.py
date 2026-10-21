"""SQLAdmin ModelViews for subscription and plan models."""

from decimal import Decimal
from typing import Any, ClassVar

from sqladmin import ModelView
from starlette.requests import Request

from app.adapters.services.payment_gateway.cashfree import CashfreeSubscriptionAdapter
from app.core.config import get_settings
from app.domain.entities.plan import BillingPeriod, Plan
from app.drivers.models.plan import PlanModel
from app.drivers.models.subscription import SubscriptionModel
from app.drivers.models.webhook_event import WebhookEventModel
from app.ports.services.payment_gateway import PaymentGateway


class PlanAdmin(ModelView, model=PlanModel):
    """Admin view for subscription plans management."""

    name = "Plan"
    name_plural = "Plans"
    icon = "fa-solid fa-tags"
    identity = "plan"

    column_list: ClassVar[list[Any]] = [
        PlanModel.id,
        PlanModel.code,
        PlanModel.name,
        PlanModel.billing_period,
        PlanModel.actual_price,
        PlanModel.offer_price,
        PlanModel.currency,
        PlanModel.max_seconds_per_request,
        PlanModel.max_usage_per_day,
        PlanModel.is_active,
        PlanModel.is_deleted,
    ]
    column_searchable_list: ClassVar[list[Any]] = [PlanModel.code, PlanModel.name]
    column_sortable_list: ClassVar[list[Any]] = [
        PlanModel.code,
        PlanModel.actual_price,
        PlanModel.offer_price,
        PlanModel.created_at,
    ]
    column_default_sort: ClassVar[list[Any]] = [(PlanModel.created_at, True)]

    form_excluded_columns: ClassVar[list[Any]] = [
        PlanModel.id,
        PlanModel.created_at,
        PlanModel.updated_at,
    ]
    can_create = True
    can_edit = False
    can_delete = True
    can_view_details = True

    def _payment_gateway(self, request: Request) -> PaymentGateway:
        gateway = getattr(request.app.state, "payment_gateway", None)
        if gateway is not None:
            return gateway
        return CashfreeSubscriptionAdapter(get_settings())

    @staticmethod
    def _plan_from_admin_data(data: dict[str, Any]) -> Plan:
        return Plan(
            code=str(data["code"]),
            name=str(data["name"]),
            billing_period=BillingPeriod.from_str(data["billing_period"]),
            actual_price=Decimal(str(data["actual_price"])),
            offer_price=Decimal(str(data["offer_price"])),
            currency=str(data.get("currency") or "INR"),
            max_seconds_per_request=int(data["max_seconds_per_request"]),
            max_usage_per_day=int(data["max_usage_per_day"]),
            is_active=bool(data.get("is_active", True)),
            is_deleted=bool(data.get("is_deleted", False)),
        )

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: Any,
        is_created: bool,
        request: Request,
    ) -> None:
        """Mirror newly created plans to the payment provider before saving locally."""
        if not is_created:
            return

        plan = self._plan_from_admin_data(data)
        if plan.is_deleted:
            return

        await self._payment_gateway(request).create_plan(plan)

    async def on_model_delete(self, model: Any, request: Request) -> None:
        """Mirror admin plan deletion to the payment provider before local deletion."""
        if model is None:
            return

        await self._payment_gateway(request).delete_plan(str(model.code))


class SubscriptionAdmin(ModelView, model=SubscriptionModel):
    """Admin view for user subscriptions oversight."""

    name = "Subscription"
    name_plural = "Subscriptions"
    icon = "fa-solid fa-credit-card"
    identity = "subscription"

    column_list: ClassVar[list[Any]] = [
        SubscriptionModel.id,
        SubscriptionModel.user_id,
        SubscriptionModel.status,
        SubscriptionModel.is_active,
        SubscriptionModel.provider,
        SubscriptionModel.snapshot_plan_name,
        SubscriptionModel.current_period_start,
        SubscriptionModel.current_period_end,
        SubscriptionModel.created_at,
    ]
    column_searchable_list: ClassVar[list[Any]] = [
        SubscriptionModel.user_id,
        SubscriptionModel.external_subscription_id,
    ]
    column_sortable_list: ClassVar[list[Any]] = [
        SubscriptionModel.status,
        SubscriptionModel.is_active,
        SubscriptionModel.current_period_end,
        SubscriptionModel.created_at,
    ]
    column_default_sort: ClassVar[list[Any]] = [(SubscriptionModel.created_at, True)]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True


class WebhookEventAdmin(ModelView, model=WebhookEventModel):
    """Admin view for payment webhook audit logs."""

    name = "Webhook Event"
    name_plural = "Webhook Events"
    icon = "fa-solid fa-bolt"
    identity = "webhook-event"

    column_list: ClassVar[list[Any]] = [
        WebhookEventModel.id,
        WebhookEventModel.event_id,
        WebhookEventModel.event_type,
        WebhookEventModel.status,
        WebhookEventModel.processed_at,
    ]
    column_searchable_list: ClassVar[list[Any]] = [
        WebhookEventModel.event_id,
        WebhookEventModel.event_type,
    ]
    column_sortable_list: ClassVar[list[Any]] = [
        WebhookEventModel.status,
        WebhookEventModel.processed_at,
    ]
    column_default_sort: ClassVar[list[Any]] = [(WebhookEventModel.processed_at, True)]

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
