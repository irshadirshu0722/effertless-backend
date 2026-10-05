"""Tests for system health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Health check liveness endpoint returns status 200 and ok status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-Id"]


@pytest.mark.asyncio
async def test_request_id_is_propagated(async_client: AsyncClient):
    request_id = "smoke-request-id"

    response = await async_client.get("/health", headers={"X-Request-Id": request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == request_id


@pytest.mark.asyncio
async def test_readiness_check(async_client: AsyncClient):
    """Readiness endpoint returns dependency status."""
    response = await async_client.get("/health/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("ready", "degraded")
    assert set(data["dependencies"]) == {"postgres", "redis"}
