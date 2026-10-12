"""Effortless API — FastAPI application factory.

This module creates and configures the FastAPI application instance.
All route registration, middleware setup, and error handler configuration
happens here. No business logic should exist in this file.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

from app.adapters.gcp_identity import GcpIdentityVerifier
from app.admin.setup import setup_admin
from app.api.routes import health, v1
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.drivers.database import create_engine
from app.ports.authentication import IdentityVerifier

request_logger = logging.getLogger("app.requests")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan handler for startup and shutdown events."""
    settings = get_settings()
    setup_logging(settings.log_level)

    logger = logging.getLogger(__name__)
    logger.info(
        "Starting %s (env=%s, debug=%s)",
        settings.app_name,
        settings.app_env,
        settings.app_debug,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app(
    settings: Settings | None = None,
    verifier: IdentityVerifier | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with routes and error handlers registered.
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered voice translation backend for the Effortless keyboard",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid4())
        request.state.request_id = request_id
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            print("Enter")
            duration_ms = (perf_counter() - started_at) * 1000
            request_logger.exception(
                "Request failed method=%s path=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                duration_ms,
                extra={"request_id": request_id},
            )
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        response.headers["X-Request-Id"] = request_id
        request_logger.info(
            "Request completed method=%s path=%s status_code=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )
        return response

    # Register exception handlers
    register_exception_handlers(app)

    # System routes (no version prefix)
    app.include_router(health.router)

    # API v1 routes
    app.include_router(v1.router, prefix="/api/v1")

    # SQLAdmin dashboard
    if settings.database_url:
        engine = create_engine(settings)
        identity_verifier = verifier or GcpIdentityVerifier(settings)
        setup_admin(app=app, engine=engine, verifier=identity_verifier)

    return app


# Application instance used by uvicorn
app = create_app()
