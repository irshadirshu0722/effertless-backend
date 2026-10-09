"""Tests for authentication and authorization error contracts."""

from app.core.exceptions import (
    AuthenticationRequiredError,
    AuthorizationFailedError,
    AuthTokenRevokedError,
    InvalidAuthTokenError,
)


def test_authentication_required_error_contract() -> None:
    error = AuthenticationRequiredError()

    assert error.code == "AUTHENTICATION_REQUIRED"
    assert error.status_code == 401


def test_invalid_auth_token_error_contract() -> None:
    error = InvalidAuthTokenError()

    assert error.code == "INVALID_AUTH_TOKEN"
    assert error.status_code == 401


def test_auth_token_revoked_error_contract() -> None:
    error = AuthTokenRevokedError()

    assert error.code == "AUTH_TOKEN_REVOKED"
    assert error.status_code == 401


def test_authorization_failed_error_contract() -> None:
    error = AuthorizationFailedError()

    assert error.code == "AUTHORIZATION_FAILED"
    assert error.status_code == 403
