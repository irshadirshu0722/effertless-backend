"""FastAPI dependency injection providers.

All injectable dependencies (settings, clients, services) are defined here.
Route handlers access them via Depends(). This keeps DI wiring in one place
and out of business logic.

Usage in routes:
    from app.api.dependencies import get_settings
    @router.get("/example")
    async def example(settings: Settings = Depends(get_settings)):
        ...
"""

from typing import Annotated

from fastapi import Depends, Header, WebSocket

from app.adapters.gcp_identity import GcpIdentityVerifier
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationRequiredError, InvalidAuthTokenError
from app.domain.entities.authenticated_user import AuthenticatedUser
from app.ports.authentication import IdentityVerifier

__all__ = [
    "Settings",
    "authenticate_websocket",
    "get_current_user",
    "get_identity_verifier",
    "get_settings",
]


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


# Future dependencies will be added here:
#
# def get_sarvam_client(settings: Settings = Depends(get_settings)) -> AsyncSarvamAI:
#     return AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)
#
# def get_speech_provider(client = Depends(get_sarvam_client)) -> SpeechProvider:
#     return SarvamSpeechProvider(client)
#
# def get_translation_provider(client = Depends(get_sarvam_client)) -> TranslationProvider:
#     return SarvamTranslationProvider(client)
