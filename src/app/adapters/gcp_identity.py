"""GCP Identity Platform authentication adapter."""

import asyncio
from collections.abc import Callable, Mapping
from typing import Any

import firebase_admin
from firebase_admin import App, auth

from app.core.config import Settings
from app.core.exceptions import AuthTokenRevokedError, InvalidAuthTokenError
from app.domain.entities.authenticated_user import AuthenticatedUser

VerifyToken = Callable[[str, App | None, bool], Mapping[str, Any]]


class GcpIdentityVerifier:
    """Verify GCP Identity Platform ID tokens with Firebase Admin SDK."""

    def __init__(
        self,
        settings: Settings,
        *,
        app: App | None = None,
        verify_token: VerifyToken | None = None,
    ) -> None:
        self._settings = settings
        self._app = app
        self._verify_token = verify_token or self._verify_with_sdk

    async def verify_token(self, token: str) -> AuthenticatedUser:
        if not token:
            raise InvalidAuthTokenError()

        try:
            decoded_token = await asyncio.to_thread(
                self._verify_token,
                token,
                self._firebase_app(),
                self._settings.auth_check_revoked,
            )
        except auth.RevokedIdTokenError as error:
            raise AuthTokenRevokedError() from error
        except (
            auth.ExpiredIdTokenError,
            auth.InvalidIdTokenError,
            auth.UserDisabledError,
            ValueError,
        ) as error:
            from main import request_logger

            request_logger.warning(
                "Firebase token verification failed: %s",
                type(error).__name__,
            )
            raise InvalidAuthTokenError() from error
        return self._to_authenticated_user(decoded_token)

    def _firebase_app(self) -> App:
        if self._app is not None:
            return self._app

        if not self._settings.gcp_project_id:
            raise InvalidAuthTokenError()

        try:
            self._app = firebase_admin.get_app()
        except ValueError:
            self._app = firebase_admin.initialize_app(
                options={"projectId": self._settings.gcp_project_id}
            )
        return self._app

    @staticmethod
    def _verify_with_sdk(token: str, app: App | None, check_revoked: bool) -> Mapping[str, Any]:
        return auth.verify_id_token(token, app=app, check_revoked=check_revoked)

    @staticmethod
    def _to_authenticated_user(decoded_token: Mapping[str, Any]) -> AuthenticatedUser:
        user_id = str(decoded_token.get("uid") or decoded_token.get("sub") or "")
        if not user_id:
            raise InvalidAuthTokenError()

        email = decoded_token.get("email")
        return AuthenticatedUser(
            user_id=user_id,
            email=str(email) if email else None,
            email_verified=bool(decoded_token.get("email_verified", False)),
            claims=decoded_token,
        )
