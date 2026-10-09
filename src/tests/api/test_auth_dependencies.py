"""Tests for API authentication dependency wiring."""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, WebSocket
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from starlette.websockets import WebSocketDisconnect

from app.api.dependencies import (
    authenticate_websocket,
    extract_bearer_token,
    get_current_user,
    get_identity_verifier,
)
from app.core.exceptions import (
    AuthenticationRequiredError,
    InvalidAuthTokenError,
    register_exception_handlers,
)
from app.domain.entities.authenticated_user import AuthenticatedUser


class FakeVerifier:
    async def verify_token(self, token: str) -> AuthenticatedUser:
        if token == "valid-token":
            return AuthenticatedUser(user_id="user-1")
        raise InvalidAuthTokenError()


def create_auth_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.dependency_overrides[get_identity_verifier] = lambda: FakeVerifier()

    @app.get("/protected")
    async def protected(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> dict[str, str]:
        return {"user_id": user.user_id}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        try:
            user = await authenticate_websocket(websocket, FakeVerifier())
        except (AuthenticationRequiredError, InvalidAuthTokenError):
            await websocket.close(code=4001)
            return

        await websocket.accept()
        await websocket.send_json({"user_id": user.user_id})
        await websocket.close()

    return app


def test_extract_bearer_token() -> None:
    assert extract_bearer_token("Bearer token-1") == "token-1"


@pytest.mark.parametrize("authorization", [None, ""])
def test_extract_bearer_token_requires_header(authorization: str | None) -> None:
    with pytest.raises(AuthenticationRequiredError):
        extract_bearer_token(authorization)


@pytest.mark.parametrize("authorization", ["Basic token", "Bearer", "Bearer   "])
def test_extract_bearer_token_rejects_malformed_header(authorization: str) -> None:
    with pytest.raises(InvalidAuthTokenError):
        extract_bearer_token(authorization)


@pytest.mark.asyncio
async def test_get_current_user_accepts_valid_bearer_token() -> None:
    app = create_auth_test_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    assert response.json() == {"user_id": "user-1"}


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_bearer_token() -> None:
    app = create_auth_test_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_bearer_token() -> None:
    app = create_auth_test_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_AUTH_TOKEN"


def test_authenticate_websocket_accepts_authorization_header() -> None:
    app = create_auth_test_app()

    with (
        TestClient(app) as client,
        client.websocket_connect(
            "/ws",
            headers={"Authorization": "Bearer valid-token"},
        ) as websocket,
    ):
        assert websocket.receive_json() == {"user_id": "user-1"}


def test_authenticate_websocket_accepts_access_token_query_param() -> None:
    app = create_auth_test_app()

    with (
        TestClient(app) as client,
        client.websocket_connect("/ws?access_token=valid-token") as websocket,
    ):
        assert websocket.receive_json() == {"user_id": "user-1"}


def test_authenticate_websocket_rejects_missing_token() -> None:
    app = create_auth_test_app()

    with TestClient(app) as client, pytest.raises(WebSocketDisconnect) as exc_info:
        client.websocket_connect("/ws").__enter__()

    assert exc_info.value.code == 4001
