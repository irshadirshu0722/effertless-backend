"""Pydantic schemas for subscription endpoints."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlanResponse(BaseModel):
    """Public subscription plan details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    actual_price: Decimal
    offer_price: Decimal
    currency: str
    monthly_seconds: int


class PlansListResponse(BaseModel):
    """List of active subscription plans."""

    plans: list[PlanResponse]


class TierLimitsSchema(BaseModel):
    """Maximum limits permitted for the user's tier."""

    model_config = ConfigDict(from_attributes=True)

    max_seconds_per_request: int
    max_usage_per_day: int


class UsageTodaySchema(BaseModel):
    """Daily request consumption stats."""

    used: int
    limit: int
    remaining: int


class UserSubscriptionResponse(BaseModel):
    """Current subscription status, limits, and today's usage."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    is_active: bool
    plan_name: str
    current_period_end: datetime | None = None
    limits: TierLimitsSchema
    usage_today: UsageTodaySchema


class CheckoutRequest(BaseModel):
    """Initiate subscription checkout request."""

    plan_code: str = Field(min_length=1, description="Unique plan code")
    return_url: str = Field(min_length=1, description="Redirect URL after payment")
    replace: bool = Field(
        default=False,
        description="Replace the current subscription immediately instead of waiting for its period to end.",
    )


class CheckoutResponse(BaseModel):
    """Checkout session response containing gateway identifiers."""

    subscription_id: str
    checkout_session_id: str
    status: str = "pending"


class CancelSubscriptionResponse(BaseModel):
    """Subscription cancellation response."""

    status: str
    current_period_end: datetime | None = None


class WebhookResponse(BaseModel):
    """Response returned to the payment gateway webhook."""

    status: str = "acknowledged"
