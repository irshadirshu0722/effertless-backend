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
