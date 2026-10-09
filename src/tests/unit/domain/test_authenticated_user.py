"""Tests for provider-independent authenticated user identity."""

import pytest

from app.domain.entities.authenticated_user import AuthenticatedUser


def test_authenticated_user_requires_user_id() -> None:
    with pytest.raises(ValueError, match="user_id"):
        AuthenticatedUser(user_id="")


def test_authenticated_user_claims_are_immutable() -> None:
    user = AuthenticatedUser(user_id="user-1", claims={"role": "tester"})

    with pytest.raises(TypeError):
        user.claims["role"] = "admin"
