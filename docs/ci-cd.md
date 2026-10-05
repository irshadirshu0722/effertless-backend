# Backend CI/CD

This repository contains the Effortless Python backend. GitHub Actions validates the root-level Poetry project and Docker image.

## Checks

The backend workflow runs on pushes and pull requests:

```bash
poetry install --no-interaction --no-ansi
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest
```

The Docker job builds the root `Dockerfile` with the repository root as its context.

## Local Parity

Run the same checks locally from the repository root:

```bash
poetry install
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest
```

Use the root [Makefile](../Makefile) for development, Compose, migration, and formatting commands.

## Secrets

Provider credentials must never be committed or printed in CI logs. Unit and integration tests use fakes and dummy values; real Sarvam, GCP Identity Platform, Cashfree, PostgreSQL, and Redis integrations must remain opt-in.
