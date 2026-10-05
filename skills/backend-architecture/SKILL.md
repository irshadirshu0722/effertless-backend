---
name: backend-architecture
description: Guidelines for the Typeless backend layered architecture (API, Application, Domain, Infrastructure)
---

# Backend Architecture Skill

## Purpose

Ensure consistent adherence to the layered backend architecture when implementing or modifying any backend component.

## When to Use

- Creating new endpoints, use cases, or domain models
- Adding new external service integrations
- Reviewing or refactoring existing code
- Making dependency injection decisions

## Architectural Principles

1. **Layer dependency rule**: API → Application → Domain ← Infrastructure. Never reverse.
2. **Domain is pure**: No framework imports (FastAPI, Pydantic, sarvamai) in `src/app/domain/`
3. **Infrastructure implements protocols**: All external integrations implement domain-defined Protocols
4. **Application orchestrates**: Use cases coordinate domain objects and infrastructure services
5. **API serializes**: Routes handle HTTP concerns only — validation, status codes, response format

## Rules

- Every new endpoint requires a corresponding use case in `src/app/application/`
- Domain models use `dataclass` or plain Python classes, NOT Pydantic `BaseModel`
- API schemas (request/response) use Pydantic `BaseModel` in `src/app/schemas/`
- Explicit mapping between API schemas and domain models (`from_domain()` / `to_domain()`)
- No business logic in route handlers

## Anti-patterns

- ❌ Importing `sarvamai` in a route handler or use case
- ❌ Returning Sarvam SDK response objects directly from an endpoint
- ❌ Putting validation logic in the infrastructure layer
- ❌ Circular imports between layers
- ❌ Using FastAPI `Depends()` in domain or application code

## Implementation Guidelines

- Use `src/app/api/dependencies.py` for all DI wiring
- Use `typing.Protocol` for all provider interfaces
- Keep use cases small — one per product action
- Name use cases after user actions: `TranslateTextUseCase`, not `TextService`

## Testing Requirements

- Unit tests for all domain models and use cases (mock infrastructure)
- Integration tests for infrastructure providers (real or contract)
- API tests using FastAPI TestClient (full stack with fakes)

## Relevant Project Documentation

- [docs/architecture/backend.md](../../docs/architecture/backend.md)
- [docs/architecture/overview.md](../../docs/architecture/overview.md)
- [docs/architecture/provider-abstraction.md](../../docs/architecture/provider-abstraction.md)

## Examples

```python
# ✅ Correct: Use case depends on protocol
class TranslateTextUseCase:
    def __init__(self, provider: TranslationProvider, registry: LanguageRegistry):
        ...

# ❌ Wrong: Use case depends on concrete provider
class TranslateTextUseCase:
    def __init__(self, client: AsyncSarvamAI):
        ...
```
