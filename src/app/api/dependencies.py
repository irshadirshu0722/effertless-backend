"""FastAPI dependency injection providers.

All injectable dependencies (settings, clients, services) are defined here.
Route handlers access them via Depends(). This keeps DI wiring in one place
and out of business logic.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, WebSocket
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.adapters.repositories import (
    PostgresPlanRepository,
    PostgresSubscriptionRepository,
    PostgresWebhookEventRepository,
)
from app.adapters.services import CashfreeSubscriptionAdapter, GcpIdentityVerifier
from app.application.use_case.check_entitlement import CheckEntitlementUseCase
from app.application.use_case.list_plans import ListPlansUseCase
from app.application.use_case.subscription.get_user_subscription import GetUserSubscriptionUseCase
from app.application.use_case.subscription.handle_subscription_webhook import (
    HandleSubscriptionWebhookUseCase,
)
from app.application.use_case.subscription.initiate_checkout import InitiateCheckoutUseCase
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationRequiredError, InvalidAuthTokenError
from app.drivers.config.database import create_engine, create_session_factory
from app.drivers.config.redis import create_redis_client
from app.ports.repository import PlanRepository, SubscriptionRepository, WebhookEventRepository
from app.ports.services import AuthenticatedUser, PaymentGateway
from app.ports.services.authentication import IdentityVerifier

__all__ = [
    "Settings",
    "authenticate_websocket",
    "get_check_entitlement_use_case",
    "get_current_user",
    "get_db_session",
    "get_handle_webhook_use_case",
    "get_identity_verifier",
    "get_initiate_checkout_use_case",
    "get_list_plans_use_case",
    "get_payment_gateway",
    "get_plan_repo",
    "get_redis_client",
    "get_settings",
    "get_subscription_repo",
    "get_user_subscription_use_case",
    "get_webhook_repo",
]


@lru_cache
def _get_engine(database_url: str) -> AsyncEngine:
    class DummySettings:
        def __init__(self, url: str):
            self.database_url = url

    return create_engine(DummySettings(database_url))  # type: ignore[arg-type]


async def get_db_session(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy database session."""
    if not settings.database_url:
        raise ValueError("DATABASE_URL must be configured")
    engine = _get_engine(settings.database_url)
    session_factory: async_sessionmaker[AsyncSession] = create_session_factory(engine)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_redis_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Redis:
    """Return configured Redis client."""
    return create_redis_client(settings)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def get_identity_verifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> IdentityVerifier:
    """Return the configured identity verifier."""
    return GcpIdentityVerifier(settings)


def extract_bearer_token(authorization: str | None) -> str:
    """Extract a bearer token from an Authorization header value."""
    if not authorization:
        raise AuthenticationRequiredError()

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise InvalidAuthTokenError()

    return token.strip()


async def get_current_user(
    verifier: Annotated[IdentityVerifier, Depends(get_identity_verifier)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthenticatedUser:
    """Verify the request bearer token and return the authenticated user."""
    token = extract_bearer_token(authorization)
    return await verifier.verify_token(token)


async def authenticate_websocket(
    websocket: WebSocket,
    verifier: IdentityVerifier,
) -> AuthenticatedUser:
    """Authenticate a WebSocket handshake before accepting the connection."""
    authorization = websocket.headers.get("authorization")
    token = websocket.query_params.get("access_token")

    if authorization:
        token = extract_bearer_token(authorization)
    elif not token:
        raise AuthenticationRequiredError()

    return await verifier.verify_token(token)


# ---------------------------------------------------------------------------
# Subscription Repositories & Adapters
# ---------------------------------------------------------------------------


def get_plan_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlanRepository:
    return PostgresPlanRepository(session)


def get_subscription_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SubscriptionRepository:
    return PostgresSubscriptionRepository(session)


def get_webhook_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WebhookEventRepository:
    return PostgresWebhookEventRepository(session)


def get_payment_gateway(
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentGateway:
    return CashfreeSubscriptionAdapter(settings)


# ---------------------------------------------------------------------------
# Subscription Use Cases
# ---------------------------------------------------------------------------


def get_list_plans_use_case(
    plan_repo: Annotated[PlanRepository, Depends(get_plan_repo)],
) -> ListPlansUseCase:
    return ListPlansUseCase(plan_repo)


def get_user_subscription_use_case(
    sub_repo: Annotated[SubscriptionRepository, Depends(get_subscription_repo)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GetUserSubscriptionUseCase:
    return GetUserSubscriptionUseCase(sub_repo, settings)


def get_initiate_checkout_use_case(
    plan_repo: Annotated[PlanRepository, Depends(get_plan_repo)],
    gateway: Annotated[PaymentGateway, Depends(get_payment_gateway)],
    sub_repo: Annotated[SubscriptionRepository, Depends(get_subscription_repo)],
) -> InitiateCheckoutUseCase:
    return InitiateCheckoutUseCase(plan_repo, gateway, sub_repo)


def get_handle_webhook_use_case(
    gateway: Annotated[PaymentGateway, Depends(get_payment_gateway)],
    webhook_repo: Annotated[WebhookEventRepository, Depends(get_webhook_repo)],
    sub_repo: Annotated[SubscriptionRepository, Depends(get_subscription_repo)],
    plan_repo: Annotated[PlanRepository, Depends(get_plan_repo)],
) -> HandleSubscriptionWebhookUseCase:
    return HandleSubscriptionWebhookUseCase(gateway, webhook_repo, sub_repo, plan_repo)


def get_check_entitlement_use_case(
    sub_repo: Annotated[SubscriptionRepository, Depends(get_subscription_repo)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CheckEntitlementUseCase:
    return CheckEntitlementUseCase(sub_repo, settings)
