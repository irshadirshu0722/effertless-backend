"""Unit tests for SQLAdmin authentication backend with JWT claims."""

import pytest
from starlette.datastructures import FormData
from starlette.requests import Request

from app.admin.auth import AdminAuth
from app.core.exceptions import InvalidAuthTokenError
from app.domain.entities.authenticated_user import AuthenticatedUser
from app.ports.authentication import IdentityVerifier


class DummyIdentityVerifier(IdentityVerifier):
    def __init__(
        self,
        users: dict[str, AuthenticatedUser],
        credentials: dict[tuple[str, str], str] | None = None,
    ) -> None:
        self.users = users
        self.credentials = credentials or {}

    async def verify_token(self, token: str) -> AuthenticatedUser:
        if token in self.users:
            return self.users[token]
        raise InvalidAuthTokenError()

    async def sign_in_with_password(self, email: str, password: str) -> str:
        if (email, password) in self.credentials:
            return self.credentials[(email, password)]
        raise InvalidAuthTokenError()


def make_request(
    form_data: dict[str, str] | None = None,
    session: dict | None = None,
    headers: dict[str, str] | None = None,
) -> Request:
    scope = {
        "type": "http",
        "method": "POST" if form_data is not None else "GET",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "session": session if session is not None else {},
    }
    request = Request(scope)
    if form_data is not None:

        async def _form():
            return FormData(form_data)

        request.form = _form  # type: ignore[method-assign]
    return request


@pytest.fixture
def auth_backend() -> AdminAuth:
    admin_user = AuthenticatedUser(
        user_id="admin-123",
        email="admin@example.com",
        claims={"role": "admin"},
    )
    normal_user = AuthenticatedUser(
        user_id="user-456",
        email="user@example.com",
        claims={"role": "user"},
    )
    no_role_user = AuthenticatedUser(
        user_id="user-789",
        email="norole@example.com",
        claims={},
    )
    verifier = DummyIdentityVerifier(
        {
            "valid-admin-token": admin_user,
            "valid-user-token": normal_user,
            "valid-no-role-token": no_role_user,
        },
        credentials={
            ("admin@example.com", "AdminPass123!"): "valid-admin-token",
            ("user@example.com", "UserPass123!"): "valid-user-token",
            ("norole@example.com", "NoRolePass123!"): "valid-no-role-token",
        },
    )
    return AdminAuth(secret_key="test-secret-key", verifier=verifier)


@pytest.mark.anyio
async def test_login_success_with_email_and_password(auth_backend: AdminAuth):
    req = make_request(form_data={"username": "admin@example.com", "password": "AdminPass123!"})
    success = await auth_backend.login(req)
    assert success is True
    assert req.session["token"] == "valid-admin-token"
    assert req.session["user_id"] == "admin-123"


@pytest.mark.anyio
async def test_login_rejected_for_user_credentials(auth_backend: AdminAuth):
    req = make_request(form_data={"username": "user@example.com", "password": "UserPass123!"})
    success = await auth_backend.login(req)
    assert success is False
    assert "token" not in req.session


@pytest.mark.anyio
async def test_login_rejected_for_norole_credentials(auth_backend: AdminAuth):
    req = make_request(form_data={"username": "norole@example.com", "password": "NoRolePass123!"})
    success = await auth_backend.login(req)
    assert success is False
    assert "token" not in req.session


@pytest.mark.anyio
async def test_login_rejected_for_wrong_password(auth_backend: AdminAuth):
    req = make_request(form_data={"username": "admin@example.com", "password": "WrongPassword"})
    success = await auth_backend.login(req)
    assert success is False
    assert "token" not in req.session


@pytest.mark.anyio
async def test_login_success_with_admin_role(auth_backend: AdminAuth):
    req = make_request(form_data={"token": "valid-admin-token"})
    success = await auth_backend.login(req)
    assert success is True
    assert req.session["token"] == "valid-admin-token"
    assert req.session["user_id"] == "admin-123"


@pytest.mark.anyio
async def test_login_via_password_field(auth_backend: AdminAuth):
    req = make_request(form_data={"username": "admin", "password": "valid-admin-token"})
    success = await auth_backend.login(req)
    assert success is True
    assert req.session["token"] == "valid-admin-token"


@pytest.mark.anyio
async def test_login_rejected_for_normal_user(auth_backend: AdminAuth):
    req = make_request(form_data={"token": "valid-user-token"})
    success = await auth_backend.login(req)
    assert success is False
    assert "token" not in req.session


@pytest.mark.anyio
async def test_login_rejected_when_role_missing(auth_backend: AdminAuth):
    req = make_request(form_data={"token": "valid-no-role-token"})
    success = await auth_backend.login(req)
    assert success is False
    assert "token" not in req.session


@pytest.mark.anyio
async def test_login_rejected_for_invalid_token(auth_backend: AdminAuth):
    req = make_request(form_data={"token": "invalid-malformed-token"})
    success = await auth_backend.login(req)
    assert success is False


@pytest.mark.anyio
async def test_login_rejected_for_empty_form(auth_backend: AdminAuth):
    req = make_request(form_data={})
    success = await auth_backend.login(req)
    assert success is False


@pytest.mark.anyio
async def test_authenticate_with_valid_admin_session(auth_backend: AdminAuth):
    req = make_request(session={"token": "valid-admin-token"})
    allowed = await auth_backend.authenticate(req)
    assert allowed is True


@pytest.mark.anyio
async def test_authenticate_denied_for_user_session(auth_backend: AdminAuth):
    req = make_request(session={"token": "valid-user-token"})
    allowed = await auth_backend.authenticate(req)
    assert allowed is False


@pytest.mark.anyio
async def test_authenticate_denied_when_role_missing_in_session(auth_backend: AdminAuth):
    req = make_request(session={"token": "valid-no-role-token"})
    allowed = await auth_backend.authenticate(req)
    assert allowed is False


@pytest.mark.anyio
async def test_authenticate_via_bearer_header(auth_backend: AdminAuth):
    req = make_request(headers={"Authorization": "Bearer valid-admin-token"})
    allowed = await auth_backend.authenticate(req)
    assert allowed is True


@pytest.mark.anyio
async def test_authenticate_denied_via_bearer_user_header(auth_backend: AdminAuth):
    req = make_request(headers={"Authorization": "Bearer valid-user-token"})
    allowed = await auth_backend.authenticate(req)
    assert allowed is False


@pytest.mark.anyio
async def test_authenticate_denied_without_token_or_session(auth_backend: AdminAuth):
    req = make_request()
    allowed = await auth_backend.authenticate(req)
    assert allowed is False


@pytest.mark.anyio
async def test_logout_clears_session(auth_backend: AdminAuth):
    session = {"token": "valid-admin-token", "user_id": "admin-123"}
    req = make_request(session=session)
    res = await auth_backend.logout(req)
    assert res is True
    assert "token" not in session
    assert "user_id" not in session
