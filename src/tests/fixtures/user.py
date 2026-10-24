import pytest

from app.domain.entities.authenticated_user import AuthenticatedUser


@pytest.fixture
def auth_user():
    return AuthenticatedUser(
        claims={}, email="test@gmail.com", email_verified=True, user_id="test-id"
    )
