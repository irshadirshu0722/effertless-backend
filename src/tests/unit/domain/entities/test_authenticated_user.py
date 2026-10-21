"""Unit tests for AuthenticatedUser."""

import pytest

from app.domain.entities.authenticated_user import AuthenticatedUser


def test_creates_authenticated_user() -> None:
    user = AuthenticatedUser(
        user_id="user-123",
        email="user@example.com",
        email_verified=True,
        claims={"role": "user", "provider": "google"},
    )

    assert user.user_id == "user-123"
    assert user.email == "user@example.com"
    assert user.email_verified is True
    assert user.claims["role"] == "user"


def test_optional_fields_use_defaults() -> None:
    user = AuthenticatedUser(user_id="user-123")

    assert user.email is None
    assert user.email_verified is False
    assert dict(user.claims) == {}


@pytest.mark.parametrize("user_id", ["", " ", "   ", "\t"])
def test_rejects_empty_or_whitespace_user_id(user_id: str) -> None:
    with pytest.raises(ValueError, match="user_id must not be empty"):
        AuthenticatedUser(user_id=user_id)


def test_claims_are_copied_from_input_mapping() -> None:
    original_claims = {"role": "user"}

    user = AuthenticatedUser(
        user_id="user-123",
        claims=original_claims,
    )

    original_claims["role"] = "admin"

    assert user.claims["role"] == "user"


def test_claims_mapping_is_read_only() -> None:
    user = AuthenticatedUser(
        user_id="user-123",
        claims={"role": "user"},
    )

    with pytest.raises(TypeError):
        user.claims["role"] = "admin"  # type: ignore[index]


def test_authenticated_user_is_frozen() -> None:
    user = AuthenticatedUser(user_id="user-123")

    with pytest.raises(AttributeError):
        user.user_id = "another-user"  # type: ignore[misc]


def test_allows_unverified_email() -> None:
    user = AuthenticatedUser(
        user_id="user-123",
        email="user@example.com",
        email_verified=False,
    )

    assert user.email == "user@example.com"
    assert user.email_verified is False
