---
name: api-design
description: API design conventions for the Typeless backend
---

# API Design Skill

## Purpose

Ensure consistent, product-driven API design across all Typeless endpoints.

## When to Use

- Creating new API endpoints
- Modifying request/response schemas
- Adding error codes
- Designing WebSocket message formats

## Architectural Principles

1. **Use-case driven**: Endpoints map to user actions, not provider operations
2. **No provider leakage**: Responses never contain Sarvam-specific data
3. **Consistent errors**: All errors follow the standard error format
4. **Versioned**: All endpoints under `/v1/`
5. **Platform-independent**: Responses work for Android, iOS, Desktop

## Rules

- Every endpoint has a Pydantic request model and response model
- Every error case has a documented error code
- All endpoints require authentication (except `GET /health`)
- Response fields use `snake_case`
- Language codes use BCP-47 format (e.g., `hi-IN`)
- Include `request_id` in all error responses
- Validate inputs before calling external services

## Anti-patterns

- ❌ Exposing raw Sarvam response fields (e.g., `sarvam_request_id`)
- ❌ Different error formats across endpoints
- ❌ Missing validation that results in Sarvam errors reaching the client
- ❌ Breaking changes within a version (`/v1/`)

## Relevant Project Documentation

- [docs/api/overview.md](../../docs/api/overview.md)
- [docs/api/errors.md](../../docs/api/errors.md)
- [docs/api/versioning.md](../../docs/api/versioning.md)
