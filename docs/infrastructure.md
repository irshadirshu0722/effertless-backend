# Local Infrastructure

Effortless runs an async FastAPI backend with PostgreSQL as the durable store and Redis as a low-latency cache.

## Services

The local Docker Compose file at `docker-compose.yml` starts PostgreSQL, Redis, and the backend. The backend exposes port `8000` and uses the source layout under `src/`.

Start it with:

```bash
make stack-up
```

Start only the backing services during local backend development with:

```bash
make infra-up
```

Run the backend directly during development with:

```bash
make dev-backend
```

The health endpoints are:

- `GET /health` returns `{"status": "ok"}`.
- `GET /health/ready` checks PostgreSQL and Redis connectivity.

## External Services

Authentication is delegated to Google Cloud Identity Platform. The backend configuration accepts `GCP_PROJECT_ID`; provider token verification and dependency wiring will be added behind ports and adapters when that feature is implemented.

Payments and subscription management are delegated to Cashfree. The backend configuration accepts `CASHFREE_APP_ID`, `CASHFREE_SECRET_KEY`, and `CASHFREE_ENVIRONMENT`. Cashfree calls must remain behind infrastructure adapters, with credentials loaded only from environment configuration.

Speech and translation remain delegated to Sarvam AI through the provider abstraction.

## Configuration

Copy the backend environment template for local development:

```bash
Copy-Item .env.example .env
```

Never commit `.env` or provider credentials. See `AGENTS.md` for the repository security rules.

## Persistence and Migrations

The database URL is supplied through `DATABASE_URL`; it is intentionally not stored in `alembic.ini`. Alembic loads the URL through the application settings in `src/migrations/env.py`.

Run migrations from the backend directory:

```bash
poetry run alembic upgrade head
```

Subscription state should remain the durable source of truth in PostgreSQL. Redis may cache frequently read subscription status, but cache eviction must never remove the durable record.
