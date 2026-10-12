"""SQLAdmin ModelViews for subscription and plan models."""

from typing import Any, ClassVar

from sqladmin import ModelView

from app.drivers.models.plan import PlanModel
from app.drivers.models.subscription import SubscriptionModel
from app.drivers.models.webhook_event import WebhookEventModel


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
    can_edit = True
    can_delete = True
    can_view_details = True


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
        SubscriptionModel.current_period_end,
        SubscriptionModel.created_at,
    ]
    column_default_sort: ClassVar[list[Any]] = [(SubscriptionModel.created_at, True)]

    can_create = False
    can_edit = True
    can_delete = False
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
