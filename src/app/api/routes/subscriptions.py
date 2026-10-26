"""FastAPI route handlers for subscription management."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from app.api.dependencies import (
    get_current_user,
    get_handle_webhook_use_case,
    get_initiate_checkout_use_case,
)
from app.application.use_case.subscription.command import (
    InitiateCheckoutCommand,
    SubscriptionWebhookCommand,
)
from app.application.use_case.subscription.initiate_checkout import (
    InitiateCheckoutUseCase,
)
from app.domain.entities.authenticated_user import AuthenticatedUser
from app.schemas.subscriptions import (
    CheckoutRequest,
    CheckoutResponse,
    WebhookResponse,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# @router.get(
#     "/plans",
#     response_model=PlansListResponse,
#     status_code=status.HTTP_200_OK,
#     summary="List available subscription plans",
# )
# async def list_plans(
#     use_case: Annotated[ListPlansUseCase, Depends(get_list_plans_use_case)],
# ) -> PlansListResponse:
#     plans = await use_case.execute()
#     return PlansListResponse(plans=[PlanResponse.model_validate(plan) for plan in plans])


# @router.get(
#     "/me",
#     response_model=UserSubscriptionResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Get current user subscription details and usage",
# )
# async def get_my_subscription(
#     current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
#     use_case: Annotated[GetUserSubscriptionUseCase, Depends(get_user_subscription_use_case)],
# ) -> UserSubscriptionResponse:
#     details = await use_case.execute(current_user.user_id)

#     pass


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
        InitiateCheckoutCommand(
            user=current_user,
            plan_code=request.plan_code,
            return_url=request.return_url,
            replace=request.replace,
        )
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
    use_case=Depends(get_handle_webhook_use_case),
    x_webhook_signature: Annotated[str | None, Header(alias="x-webhook-signature")] = None,
    x_webhook_timestamp: Annotated[str | None, Header(alias="x-webhook-timestamp")] = None,
) -> WebhookResponse:
    raw_payload = await request.body()

    try:
        event_data = json.loads(raw_payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        event_data = {}

    await use_case.execute(
        SubscriptionWebhookCommand(
            raw_payload=raw_payload,
            signature=x_webhook_signature or "",
            timestamp=x_webhook_timestamp or "",
            event_data=event_data,
        )
    )

    return WebhookResponse(status="acknowledged")


# @router.post(
#     "/cancel",
#     response_model=CancelSubscriptionResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Cancel active subscription",
# )
# async def cancel_subscription(
#     current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
#     sub_repo: Annotated[SubscriptionRepository, Depends(get_subscription_repo)],
#     gateway: Annotated[PaymentGateway, Depends(get_payment_gateway)],
# ) -> CancelSubscriptionResponse:
#     active_sub = await sub_repo.get_active_by_user_id(current_user.user_id)

#     if not active_sub or not active_sub.external_subscription_id:
#         return CancelSubscriptionResponse(
#             status="cancelled",
#             current_period_end=None,
#         )

#     await gateway.cancel_subscription(active_sub.external_subscription_id)

#     updated = Subscription(
#         id=active_sub.id,
#         user_id=active_sub.user_id,
#         plan_id=active_sub.plan_id,
#         status=SubscriptionStatus.CANCELLED,
#         provider=active_sub.provider,
#         external_subscription_id=active_sub.external_subscription_id,
#         external_customer_id=active_sub.external_customer_id,
#         current_period_start=active_sub.current_period_start,
#         current_period_end=active_sub.current_period_end,
#         cancelled_at=active_sub.cancelled_at,
#         snapshot=active_sub.snapshot,
#     )
#     await sub_repo.save(updated)

#     return CancelSubscriptionResponse(
#         status="cancelled",
#         current_period_end=active_sub.current_period_end,
#     )
