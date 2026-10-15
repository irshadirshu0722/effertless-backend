"""FastAPI route handlers for subscription management."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from app.api.dependencies import (
    get_current_user,
    get_handle_webhook_use_case,
    get_initiate_checkout_use_case,
    get_list_plans_use_case,
    get_payment_gateway,
    get_subscription_repo,
    get_user_subscription_use_case,
)
from app.application.use_case.get_user_subscription import GetUserSubscriptionUseCase
from app.application.use_case.handle_subscription_webhook import (
    HandleSubscriptionWebhookUseCase,
)
from app.application.use_case.initiate_checkout import InitiateCheckoutUseCase
from app.application.use_case.list_plans import ListPlansUseCase
from app.domain.entities.authenticated_user import AuthenticatedUser
from app.domain.entities.subscription import Subscription, SubscriptionStatus
from app.ports.subscription import PaymentGateway, SubscriptionRepository
from app.schemas.subscriptions import (
    CancelSubscriptionResponse,
    CheckoutRequest,
    CheckoutResponse,
    PlanResponse,
    PlansListResponse,
    TierLimitsSchema,
    UsageTodaySchema,
    UserSubscriptionResponse,
    WebhookResponse,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get(
    "/plans",
    response_model=PlansListResponse,
    status_code=status.HTTP_200_OK,
    summary="List available subscription plans",
)
async def list_plans(
    use_case: Annotated[ListPlansUseCase, Depends(get_list_plans_use_case)],
) -> PlansListResponse:
    plans = await use_case.execute()
    return PlansListResponse(
        plans=[
            PlanResponse(
                id=plan.id,
                code=plan.code,
                name=plan.name,
                billing_period=plan.billing_period,
                actual_price=float(plan.actual_price),
                offer_price=float(plan.offer_price),
                currency=plan.currency,
                max_seconds_per_request=plan.max_seconds_per_request,
                max_usage_per_day=plan.max_usage_per_day,
            )
            for plan in plans
        ]
    )


@router.get(
    "/me",
    response_model=UserSubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user subscription details and usage",
)
async def get_my_subscription(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[GetUserSubscriptionUseCase, Depends(get_user_subscription_use_case)],
) -> UserSubscriptionResponse:
    details = await use_case.execute(current_user.user_id)
    return UserSubscriptionResponse(
        status=details.status,
        plan_name=details.plan_name,
        current_period_end=details.current_period_end,
        limits=TierLimitsSchema(
            max_seconds_per_request=details.limits.max_seconds_per_request,
            max_usage_per_day=details.limits.max_usage_per_day,
        ),
        usage_today=UsageTodaySchema(
            used=details.usage_today.used_today,
            limit=details.usage_today.limit,
            remaining=details.usage_today.remaining,
        ),
    )


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate subscription checkout session",
)
async def create_checkout(
    request: CheckoutRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    use_case: Annotated[InitiateCheckoutUseCase, Depends(get_initiate_checkout_use_case)],
) -> CheckoutResponse:
    result = await use_case.execute(
        user=current_user,
        plan_code=request.plan_code,
        return_url=request.return_url,
    )
    return CheckoutResponse(
        subscription_id=result.subscription_id,
        checkout_session_id=result.checkout_session_id,
        status=result.status,
    )


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Cashfree subscription webhook receiver",
)
async def handle_webhook(
    request: Request,
    use_case: Annotated[HandleSubscriptionWebhookUseCase, Depends(get_handle_webhook_use_case)],
    x_webhook_signature: Annotated[str | None, Header(alias="x-webhook-signature")] = None,
    x_webhook_timestamp: Annotated[str | None, Header(alias="x-webhook-timestamp")] = None,
) -> WebhookResponse:
    raw_payload = await request.body()
    try:
        event_data = json.loads(raw_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        event_data = {}

    await use_case.execute(
        raw_payload=raw_payload,
        signature=x_webhook_signature or "",
        timestamp=x_webhook_timestamp or "",
        event_data=event_data,
    )
    return WebhookResponse(status="acknowledged")


@router.post(
    "/cancel",
    response_model=CancelSubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel active subscription",
)
async def cancel_subscription(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    sub_repo: Annotated[SubscriptionRepository, Depends(get_subscription_repo)],
    gateway: Annotated[PaymentGateway, Depends(get_payment_gateway)],
) -> CancelSubscriptionResponse:
    active_sub = await sub_repo.get_active_by_user_id(current_user.user_id)
    if active_sub and active_sub.external_subscription_id:
        await gateway.cancel_subscription(active_sub.external_subscription_id)
        updated = Subscription(
            id=active_sub.id,
            user_id=active_sub.user_id,
            plan_id=active_sub.plan_id,
            status=SubscriptionStatus.CANCELLED,
            provider=active_sub.provider,
            external_subscription_id=active_sub.external_subscription_id,
            external_customer_id=active_sub.external_customer_id,
            current_period_start=active_sub.current_period_start,
            current_period_end=active_sub.current_period_end,
            cancelled_at=active_sub.cancelled_at,
            snapshot=active_sub.snapshot,
        )
        await sub_repo.save(updated)
        return CancelSubscriptionResponse(
            status="cancelled",
            current_period_end=active_sub.current_period_end,
        )

    return CancelSubscriptionResponse(status="cancelled", current_period_end=None)
