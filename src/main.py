"""Effortless API — FastAPI application factory.

This module creates and configures the FastAPI application instance.
All route registration, middleware setup, and error handler configuration
happens here. No business logic should exist in this file.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, v1
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan handler for startup and shutdown events."""
    settings = get_settings()
    setup_logging(settings.log_level)

    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        "Starting %s (env=%s, debug=%s)",
        settings.app_name,
        settings.app_env,
        settings.app_debug,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with routes and error handlers registered.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered voice translation backend for the Effortless keyboard",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # System routes (no version prefix)
    app.include_router(health.router)

    # API v1 routes
    app.include_router(v1.router, prefix="/api/v1")

    return app


# Application instance used by uvicorn
app = create_app()
