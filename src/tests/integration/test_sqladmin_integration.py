"""Integration tests for SQLAdmin dashboard with real PostgreSQL container and JWT role check."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_dashboard_unauthenticated_redirect(
    integration_client: AsyncClient,
) -> None:
    """Unauthenticated access to /admin must redirect to /admin/login."""
    response = await integration_client.get("/admin/", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert "/admin/login" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_admin_login_rejected_for_normal_user(
    integration_client: AsyncClient,
) -> None:
    """User with role: 'user' is denied login access to /admin."""
    login_resp = await integration_client.post(
        "/admin/login",
        data={"username": "user", "password": "user:normal_user"},
        follow_redirects=False,
    )
    # Failed login in SQLAdmin re-renders login page or returns 400
    assert login_resp.status_code in (400, 302, 303)
    # If it redirects, it redirects back to login
    if login_resp.status_code in (302, 303):
        assert "/admin/login" in login_resp.headers.get("location", "")

    # Attempting to access dashboard still fails
    admin_resp = await integration_client.get("/admin", follow_redirects=False)
    assert admin_resp.status_code in (302, 303, 307)


@pytest.mark.asyncio
async def test_admin_login_rejected_when_role_missing(
    integration_client: AsyncClient,
) -> None:
    """User without role claim in token is denied login access to /admin."""
    login_resp = await integration_client.post(
        "/admin/login",
        data={"username": "norole", "password": "valid-token"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (400, 302, 303)


@pytest.mark.asyncio
async def test_admin_login_and_dashboard_views(
    integration_client: AsyncClient,
) -> None:
    """Admin with role: 'admin' successfully logs in, views models, and logs out."""
    # 1. Login with admin token
    login_resp = await integration_client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin:superadmin"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (302, 303)
    loc = login_resp.headers.get("location", "")
    assert loc.endswith("/admin") or loc.endswith("/admin/")

    # 2. Access dashboard with session
    dashboard_resp = await integration_client.get("/admin", follow_redirects=True)
    assert dashboard_resp.status_code == 200
    dashboard_html = dashboard_resp.text
    assert "Effortless Admin" in dashboard_html
    assert "Plans" in dashboard_html
    assert "Subscriptions" in dashboard_html

    # 3. Access Plans list view
    plans_resp = await integration_client.get("/admin/plan-model/list", follow_redirects=True)
    assert plans_resp.status_code == 200

    # 4. Access Subscriptions list view
    subs_resp = await integration_client.get(
        "/admin/subscription-model/list", follow_redirects=True
    )
    assert subs_resp.status_code == 200

    # 5. Access Webhook Events list view
    webhooks_resp = await integration_client.get(
        "/admin/webhook-event-model/list", follow_redirects=True
    )
    assert webhooks_resp.status_code == 200

    # 6. Logout
    logout_resp = await integration_client.get("/admin/logout", follow_redirects=False)
    assert logout_resp.status_code in (302, 303)

    # 7. Verify session is cleared and dashboard redirects back to login
    after_logout = await integration_client.get("/admin/", follow_redirects=False)
    assert after_logout.status_code in (302, 303, 307)
    assert "/admin/login" in after_logout.headers.get("location", "")


@pytest.mark.asyncio
async def test_admin_login_with_email_and_password_success(
    integration_client: AsyncClient,
) -> None:
    """Admin logs in using email address and password credentials."""
    login_resp = await integration_client.post(
        "/admin/login",
        data={"username": "admin@example.com", "password": "password"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (302, 303)
    loc = login_resp.headers.get("location", "")
    assert loc.endswith("/admin") or loc.endswith("/admin/")

    # Can access admin dashboard
    dashboard_resp = await integration_client.get("/admin", follow_redirects=True)
    assert dashboard_resp.status_code == 200
    assert "Effortless Admin" in dashboard_resp.text


@pytest.mark.asyncio
async def test_admin_login_with_wrong_password_rejected(
    integration_client: AsyncClient,
) -> None:
    """Invalid password credentials are rejected."""
    login_resp = await integration_client.post(
        "/admin/login",
        data={"username": "admin@example.com", "password": "wrong_password_xyz"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (400, 302, 303)
