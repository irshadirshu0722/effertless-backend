"""Pydantic schemas for subscription endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    """Public subscription plan details."""

    id: UUID
    code: str
    name: str
    actual_price: float
    offer_price: float
    currency: str
    max_seconds_per_request: int
    max_usage_per_day: int


class PlansListResponse(BaseModel):
    """List of active subscription plans."""

    plans: list[PlanResponse]


class TierLimitsSchema(BaseModel):
    """Max limits permitted for user's tier."""

    max_seconds_per_request: int
    max_usage_per_day: int


class UsageTodaySchema(BaseModel):
    """Daily request consumption stats."""

    used: int
    limit: int
    remaining: int


class UserSubscriptionResponse(BaseModel):
    """Current user subscription status, limits, and today's usage."""

    status: str
    is_active: bool = True
    plan_name: str
    current_period_end: datetime | None = None
    limits: TierLimitsSchema
    usage_today: UsageTodaySchema


class CheckoutRequest(BaseModel):
    """Initiate subscription checkout request."""

    plan_code: str = Field(..., min_length=1, description="Unique plan code")
    return_url: str = Field(..., min_length=1, description="Redirect URL after payment")


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
    """Response returned to payment gateway webhook call."""

    status: str = "acknowledged"
