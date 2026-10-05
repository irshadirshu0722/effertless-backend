"""Health and readiness check endpoints."""

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings

router = APIRouter(tags=["System"])


@router.get("/health", summary="Liveness probe")
async def health_check() -> dict:
    """Return application liveness status.

    Returns:
        Simple status response confirming the service process is alive.
    """
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe")
async def readiness_check() -> JSONResponse:
    """Return readiness for configured PostgreSQL and Redis services."""
    settings = get_settings()
    postgres_ok = await _check_tcp_port(settings.postgres_host, settings.postgres_port)
    redis_ok = await _check_tcp_port(settings.redis_host, settings.redis_port)
    all_ready = postgres_ok and redis_ok

    return JSONResponse(
        status_code=200 if all_ready else 503,
        content={
            "status": "ready" if all_ready else "degraded",
            "dependencies": {
                "postgres": "connected" if postgres_ok else "unreachable",
                "redis": "connected" if redis_ok else "unreachable",
            },
        },
    )


async def _check_tcp_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check whether a configured infrastructure port accepts connections."""
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, TimeoutError):
        return False
