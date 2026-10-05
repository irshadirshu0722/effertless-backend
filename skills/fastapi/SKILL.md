---
name: fastapi
description: FastAPI-specific conventions, patterns, and best practices for the Typeless backend
---

# FastAPI Skill

## Purpose

Ensure consistent FastAPI usage patterns across the Typeless backend.

## When to Use

- Creating or modifying API routes
- Setting up middleware
- Configuring dependency injection
- Handling WebSocket endpoints
- Setting up error handlers

## Architectural Principles

1. **Async everything**: All route handlers and dependencies are `async def`
2. **Pydantic for validation**: All request/response bodies use Pydantic models
3. **Auto-generated OpenAPI**: Leverage FastAPI's automatic documentation
4. **Dependency injection**: Use `Depends()` for service wiring
5. **Exception handlers**: Centralized error handling via `app.exception_handler()`

## Rules

- All routes must have explicit `response_model` type hints
- All routes must have docstrings (appear in OpenAPI docs)
- WebSocket routes must validate auth before `websocket.accept()`
- Use `status_code` parameter for non-200 success responses
- Never use `Response` directly; use typed response models

## Anti-patterns

- ❌ Blocking I/O in route handlers (use `async`)
- ❌ Catching all exceptions silently in routes
- ❌ Using global mutable state
- ❌ Returning `dict` instead of Pydantic models
- ❌ Hardcoding CORS origins

## Implementation Guidelines

```python
# App factory pattern
def create_app() -> FastAPI:
    app = FastAPI(title="Typeless API", version="0.1.0")
    app.include_router(health_router)
    app.include_router(v1_router, prefix="/v1")
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(AppError, app_error_handler)
    return app
```

## Testing Requirements

- Use `httpx.AsyncClient` with `app` for API tests
- Use `TestClient` for synchronous test scenarios
- WebSocket tests must test both happy path and error cases

## Relevant Project Documentation

- [docs/architecture/backend.md](../../docs/architecture/backend.md)
- [docs/api/overview.md](../../docs/api/overview.md)
