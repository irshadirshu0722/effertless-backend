"""SQLAdmin initialization and configuration."""

from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine

from app.drivers.admin_dashboard.auth import AdminAuth
from app.drivers.admin_dashboard.views import PlanAdmin, SubscriptionAdmin, WebhookEventAdmin
from app.ports.services.authentication import IdentityVerifier


def setup_admin(
    app: FastAPI,
    engine: AsyncEngine,
    verifier: IdentityVerifier,
    secret_key: str = "effortless-admin-session-secret",
) -> Admin:
    """Mount and configure SQLAdmin dashboard on the FastAPI application."""
    auth_backend = AdminAuth(secret_key=secret_key, verifier=verifier)
    admin = Admin(
        app=app,
        engine=engine,
        title="Effortless Admin",
        base_url="/admin",
        authentication_backend=auth_backend,
    )
    admin.add_view(PlanAdmin)
    admin.add_view(SubscriptionAdmin)
    admin.add_view(WebhookEventAdmin)
    return admin
