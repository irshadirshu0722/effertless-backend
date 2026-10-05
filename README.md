# Effortless Backend

FastAPI backend service powering the Effortless AI voice translation keyboard.

## Architecture

The backend follows Clean Architecture principles:

```
./
├── src/
│   ├── app/             # Backend Clean Architecture package
│   │   ├── adapters/    # External-system adapters
│   │   ├── api/         # HTTP & WebSocket endpoints
│   │   ├── application/ # Use cases and application services
│   │   ├── core/        # Configuration, logging, and exceptions
│   │   ├── domain/      # Entities, value objects, and business logic
│   │   ├── drivers/     # Concrete infrastructure drivers
│   │   ├── ports/       # Application-facing abstractions
│   │   └── schemas/     # Pydantic API schemas
│   ├── migrations/      # Alembic migrations
│   ├── tests/           # Pytest unit, integration, and API tests
│   └── main.py          # FastAPI application entry point
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Prerequisites

- Python >= 3.12
- [Poetry](https://python-poetry.org/) package manager

## Quickstart

### 1. Install Dependencies

```bash
poetry install
```

### 2. Configure Environment

```bash
Copy-Item .env.example .env
# Edit .env and supply your SARVAM_API_KEY
```

### 3. Run Development Server

```bash
poetry run uvicorn --app-dir src main:app --reload --port 8000
```

Verify health check:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

API documentation (available in debug mode):

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development Commands

| Command                            | Action                |
| ---------------------------------- | --------------------- |
| `poetry run pytest`                | Run test suite        |
| `poetry run ruff check .`          | Run linter            |
| `poetry run ruff format --check .` | Check code formatting |
| `poetry run ruff format .`         | Format code           |

## Docker Build & Run

```bash
docker build -t effortless-backend .
docker run -p 8000:8000 --env-file .env effortless-backend
```
