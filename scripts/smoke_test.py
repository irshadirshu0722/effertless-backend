"""Minimal runtime smoke test for the local backend stack."""

import asyncio
import os
import sys

import asyncpg
import httpx
from redis.asyncio import Redis

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:8000")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/effortless",
).replace("postgresql+asyncpg://", "postgresql://", 1)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def check_application() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=3.0) as client:
        health_response = await client.get("/health")
        if health_response.status_code != 200:
            raise RuntimeError(f"application health failed: HTTP {health_response.status_code}")

        readiness_response = await client.get("/health/ready")
        if readiness_response.status_code != 200:
            raise RuntimeError(
                f"application readiness failed: HTTP {readiness_response.status_code}"
            )


async def check_postgres() -> None:
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        result = await connection.fetchval("SELECT 1")
        if result != 1:
            raise RuntimeError("PostgreSQL SELECT 1 returned an unexpected result")
    finally:
        await connection.close()


async def check_redis() -> None:
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        if not await client.ping():
            raise RuntimeError("Redis PING failed")
    finally:
        await client.aclose()


async def run_smoke_test() -> None:
    await check_application()
    await check_postgres()
    await check_redis()


if __name__ == "__main__":
    try:
        asyncio.run(run_smoke_test())
    except (OSError, RuntimeError, httpx.HTTPError, asyncpg.PostgresError) as error:
        print(f"Smoke test failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    else:
        print("Smoke test passed: application, PostgreSQL, and Redis are healthy.")
