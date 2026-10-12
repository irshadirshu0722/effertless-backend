"""Tests for the GCP Identity Platform verifier adapter."""

import pytest
from firebase_admin import auth

from app.adapters.gcp_identity import GcpIdentityVerifier
from app.core.config import Settings
from app.core.exceptions import AuthTokenRevokedError, InvalidAuthTokenError


@pytest.mark.asyncio
async def test_gcp_identity_verifier_maps_claims_to_user() -> None:
    def verify_token(token, app, check_revoked):
        assert token == "token-1"
        assert app == "firebase-app"
        assert check_revoked is True
        return {
            "uid": "user-1",
            "email": "user@example.com",
            "email_verified": True,
            "tenant_id": "tenant-1",
        }

    verifier = GcpIdentityVerifier(
        Settings(gcp_project_id="project-1", auth_check_revoked=True),
        app="firebase-app",
        verify_token=verify_token,
    )

    user = await verifier.verify_token("token-1")

    assert user.user_id == "user-1"
    assert user.email == "user@example.com"
    assert user.email_verified is True
    assert user.claims["tenant_id"] == "tenant-1"


@pytest.mark.asyncio
async def test_gcp_identity_verifier_uses_sub_when_uid_missing() -> None:
    def verify_token(token, app, check_revoked):
        return {"sub": "subject-1"}

    verifier = GcpIdentityVerifier(
        Settings(gcp_project_id="project-1"),
        app="firebase-app",
        verify_token=verify_token,
    )

    user = await verifier.verify_token("token-1")

    assert user.user_id == "subject-1"


@pytest.mark.asyncio
async def test_gcp_identity_verifier_rejects_missing_subject() -> None:
    def verify_token(token, app, check_revoked):
        return {"email": "user@example.com"}

    verifier = GcpIdentityVerifier(
        Settings(gcp_project_id="project-1"),
        app="firebase-app",
        verify_token=verify_token,
    )

    with pytest.raises(InvalidAuthTokenError):
        await verifier.verify_token("token-1")


@pytest.mark.asyncio
async def test_gcp_identity_verifier_maps_revoked_token() -> None:
    def verify_token(token, app, check_revoked):
        raise auth.RevokedIdTokenError("revoked")

    verifier = GcpIdentityVerifier(
        Settings(gcp_project_id="project-1"),
        app="firebase-app",
        verify_token=verify_token,
    )

    with pytest.raises(AuthTokenRevokedError):
        await verifier.verify_token("token-1")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        auth.ExpiredIdTokenError("expired", None),
        auth.InvalidIdTokenError("invalid"),
        auth.UserDisabledError("disabled"),
        ValueError("bad token"),
    ],
)
async def test_gcp_identity_verifier_maps_invalid_tokens(error: Exception) -> None:
    def verify_token(token, app, check_revoked):
        raise error

    verifier = GcpIdentityVerifier(
        Settings(gcp_project_id="project-1"),
        app="firebase-app",
        verify_token=verify_token,
    )

    with pytest.raises(InvalidAuthTokenError):
        await verifier.verify_token("token-1")


@pytest.mark.asyncio
async def test_gcp_identity_sign_in_with_password_success() -> None:
    import json

    import httpx

    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "idToken": "mocked-id-token-123",
                "localId": "mocked-uid-456",
                "expiresIn": "3600",
            },
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    verifier = GcpIdentityVerifier(
        Settings(gcp_identity_web_api_key="test-api-key"),
        client=mock_client,
    )

    token = await verifier.sign_in_with_password("test@example.com", "secretpass")
    assert token == "mocked-id-token-123"
    assert len(captured_requests) == 1
    assert "key=test-api-key" in str(captured_requests[0].url)
    body = json.loads(captured_requests[0].content)
    assert body["email"] == "test@example.com"
    assert body["password"] == "secretpass"
    assert body["returnSecureToken"] is True


@pytest.mark.asyncio
async def test_gcp_identity_sign_in_missing_api_key() -> None:
    verifier = GcpIdentityVerifier(Settings(gcp_identity_web_api_key=""))
    with pytest.raises(InvalidAuthTokenError):
        await verifier.sign_in_with_password("test@example.com", "secretpass")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("", "secretpass"),
        ("test@example.com", ""),
    ],
)
async def test_gcp_identity_sign_in_empty_credentials(email: str, password: str) -> None:
    verifier = GcpIdentityVerifier(Settings(gcp_identity_web_api_key="test-key"))
    with pytest.raises(InvalidAuthTokenError):
        await verifier.sign_in_with_password(email, password)


@pytest.mark.asyncio
async def test_gcp_identity_sign_in_error_response() -> None:
    import httpx

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"code": 400, "message": "INVALID_PASSWORD"}},
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    verifier = GcpIdentityVerifier(
        Settings(gcp_identity_web_api_key="test-api-key"),
        client=mock_client,
    )

    with pytest.raises(InvalidAuthTokenError):
        await verifier.sign_in_with_password("test@example.com", "wrongpass")


@pytest.mark.asyncio
async def test_gcp_identity_sign_in_network_error() -> None:
    import httpx

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Network down")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    verifier = GcpIdentityVerifier(
        Settings(gcp_identity_web_api_key="test-api-key"),
        client=mock_client,
    )

    with pytest.raises(InvalidAuthTokenError):
        await verifier.sign_in_with_password("test@example.com", "secretpass")
