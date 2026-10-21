import sys
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from firebase_admin import auth

from app.adapters.services import GcpIdentityVerifier
from app.core.exceptions import AuthTokenRevokedError, InvalidAuthTokenError


@pytest.fixture
def settings():
    """Minimal settings required by GcpIdentityVerifier."""
    return SimpleNamespace(
        gcp_project_id="test-project",
        gcp_identity_web_api_key="test-api-key",
        auth_check_revoked=False,
    )


@pytest.fixture
def decoded_token():
    return {
        "uid": "user-123",
        "sub": "user-123",
        "email": "user@example.com",
        "email_verified": True,
        "role": "user",
    }


@pytest.fixture
def verify_token_mock(decoded_token):
    return Mock(return_value=decoded_token)


@pytest.fixture
def verifier(settings, verify_token_mock):
    # Passing an app prevents Firebase initialization in ordinary unit tests.
    fake_app = object()

    return GcpIdentityVerifier(
        settings,
        app=fake_app,
        verify_token=verify_token_mock,
    )


@pytest.fixture
def mock_request_logger(monkeypatch):
    """Prevent error-path tests from depending on the real application entry point."""
    logger = Mock()
    monkeypatch.setitem(
        sys.modules,
        "main",
        SimpleNamespace(request_logger=logger),
    )
    return logger


# ---------------------------------------------------------------------------
# ID token verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_token_returns_authenticated_user(
    verifier,
    verify_token_mock,
    decoded_token,
):
    user = await verifier.verify_token("valid-token")

    assert user.user_id == "user-123"
    assert user.email == "user@example.com"
    assert user.email_verified is True
    assert user.claims["role"] == "user"

    verify_token_mock.assert_called_once_with(
        "valid-token",
        verifier._app,
        False,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("token", ["", None])
async def test_verify_token_rejects_empty_token(verifier, verify_token_mock, token):
    with pytest.raises(InvalidAuthTokenError):
        await verifier.verify_token(token)

    verify_token_mock.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception",
    [
        auth.ExpiredIdTokenError(
            message="Token expired",
            cause=ValueError("expired"),
        ),
        auth.InvalidIdTokenError(
            message="Invalid token",
            cause=ValueError("invalid"),
        ),
        auth.UserDisabledError(
            message="User disabled",
            cause=ValueError("disabled"),
        ),
        ValueError("invalid token"),
    ],
    ids=["expired", "invalid", "disabled-user", "value-error"],
)
async def test_verify_token_rejects_invalid_tokens(
    settings,
    exception,
    mock_request_logger,
):
    verify = Mock(side_effect=exception)
    verifier = GcpIdentityVerifier(
        settings,
        app=object(),
        verify_token=verify,
    )

    with pytest.raises(InvalidAuthTokenError):
        await verifier.verify_token("bad-token")

    mock_request_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_verify_token_rejects_revoked_token(settings):
    verifier = GcpIdentityVerifier(
        settings,
        app=object(),
        verify_token=Mock(side_effect=auth.RevokedIdTokenError("revoked")),
    )

    with pytest.raises(AuthTokenRevokedError):
        await verifier.verify_token("revoked-token")


@pytest.mark.asyncio
async def test_verify_token_passes_revocation_setting(settings, decoded_token):
    settings.auth_check_revoked = True
    verify = Mock(return_value=decoded_token)

    verifier = GcpIdentityVerifier(
        settings,
        app=object(),
        verify_token=verify,
    )

    await verifier.verify_token("valid-token")

    assert verify.call_args.args[2] is True


# ---------------------------------------------------------------------------
# Decoded token -> domain entity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "decoded",
    [
        {},
        {"email": "user@example.com"},
        {"uid": "", "sub": ""},
        {"uid": None, "sub": None},
    ],
)
def test_to_authenticated_user_rejects_missing_user_id(decoded):
    with pytest.raises(InvalidAuthTokenError):
        GcpIdentityVerifier._to_authenticated_user(decoded)


def test_to_authenticated_user_supports_sub_claim():
    user = GcpIdentityVerifier._to_authenticated_user(
        {"sub": "subject-456", "email_verified": False}
    )

    assert user.user_id == "subject-456"
    assert user.email is None
    assert user.email_verified is False


def test_to_authenticated_user_preserves_claims(decoded_token):
    user = GcpIdentityVerifier._to_authenticated_user(decoded_token)

    assert user.claims["uid"] == decoded_token["uid"]
    assert user.claims["role"] == "user"


# ---------------------------------------------------------------------------
# Firebase app initialization
# ---------------------------------------------------------------------------


def test_firebase_app_returns_injected_app(settings):
    injected_app = object()
    verifier = GcpIdentityVerifier(settings, app=injected_app)

    assert verifier._firebase_app() is injected_app


@pytest.mark.asyncio
async def test_verify_token_rejects_missing_project_id(settings):
    settings.gcp_project_id = None

    verifier = GcpIdentityVerifier(
        settings,
        verify_token=Mock(),
    )

    with pytest.raises(InvalidAuthTokenError):
        await verifier.verify_token("valid-token")


def test_firebase_app_reuses_default_app(settings, monkeypatch):
    existing_app = object()

    monkeypatch.setattr(
        "app.adapters.services.authentication_service.gcp_identity.firebase_admin.get_app",
        Mock(return_value=existing_app),
    )

    initialize = Mock()
    monkeypatch.setattr(
        "app.adapters.services.authentication_service.gcp_identity.firebase_admin.initialize_app",
        initialize,
    )

    verifier = GcpIdentityVerifier(settings)

    assert verifier._firebase_app() is existing_app
    initialize.assert_not_called()


def test_firebase_app_initializes_when_no_default_app(settings, monkeypatch):
    initialized_app = object()

    def get_app():
        raise ValueError("No app exists")

    initialize = Mock(return_value=initialized_app)

    monkeypatch.setattr(
        "app.adapters.services.authentication_service.gcp_identity.firebase_admin.get_app",
        get_app,
    )
    monkeypatch.setattr(
        "app.adapters.services.authentication_service.gcp_identity.firebase_admin.initialize_app",
        initialize,
    )

    verifier = GcpIdentityVerifier(settings)

    assert verifier._firebase_app() is initialized_app
    initialize.assert_called_once_with(options={"projectId": settings.gcp_project_id})


# ---------------------------------------------------------------------------
# Password sign-in HTTP API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sign_in_with_password_returns_id_token(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("accounts:signInWithPassword")
        assert request.url.params["key"] == "test-api-key"

        import json

        payload = json.loads(request.content)
        assert payload["email"] == "user@example.com"
        assert payload["password"] == "correct-password"
        assert payload["returnSecureToken"] is True

        return httpx.Response(
            200,
            json={"idToken": "issued-id-token"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier = GcpIdentityVerifier(settings, client=client)

        token = await verifier.sign_in_with_password(
            "user@example.com",
            "correct-password",
        )

    assert token == "issued-id-token"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("", "password"),
        ("user@example.com", ""),
        ("", ""),
    ],
)
async def test_sign_in_rejects_empty_credentials(settings, email, password):
    verifier = GcpIdentityVerifier(settings)

    with pytest.raises(InvalidAuthTokenError):
        await verifier.sign_in_with_password(email, password)


@pytest.mark.asyncio
async def test_sign_in_rejects_missing_api_key(settings, mock_request_logger):
    settings.gcp_identity_web_api_key = None
    verifier = GcpIdentityVerifier(settings)

    with pytest.raises(InvalidAuthTokenError):
        await verifier.sign_in_with_password(
            "user@example.com",
            "password",
        )

    mock_request_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_sign_in_rejects_gcp_error_response(
    settings,
    mock_request_logger,
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "INVALID_PASSWORD",
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier = GcpIdentityVerifier(settings, client=client)

        with pytest.raises(InvalidAuthTokenError):
            await verifier.sign_in_with_password(
                "user@example.com",
                "wrong-password",
            )

    mock_request_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_sign_in_rejects_response_without_id_token(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"expiresIn": "3600"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier = GcpIdentityVerifier(settings, client=client)

        with pytest.raises(InvalidAuthTokenError):
            await verifier.sign_in_with_password(
                "user@example.com",
                "password",
            )


@pytest.mark.asyncio
async def test_sign_in_rejects_network_error(
    settings,
    mock_request_logger,
):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier = GcpIdentityVerifier(settings, client=client)

        with pytest.raises(InvalidAuthTokenError):
            await verifier.sign_in_with_password(
                "user@example.com",
                "password",
            )

    mock_request_logger.warning.assert_called_once()
