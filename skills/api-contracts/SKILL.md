---
name: api-contracts
description: Contract-first API development rules between backend and client
---

# Purpose

Guarantees contract synchronization between the Python FastAPI backend and Kotlin Multiplatform client.

# Scope

`docs/contracts/`, backend Pydantic schemas (`src/app/schemas/`), and external client DTOs.

# When to use

Use whenever adding new endpoints, changing field names, updating data types, or adding query parameters.

# Architecture rules

- **Never change contracts in isolation**: When an API changes, update `docs/contracts/api-contract.md`, the affected `src/app/` code, and backend tests simultaneously.
- Always use explicit `@SerialName` annotations on client DTOs matching backend snake_case fields.
- Backward compatibility must be preserved on all published endpoints (`/api/v1/`).

# Preferred patterns

- Shared specifications in `docs/contracts/api-contract.md`.
- Contract tests verifying serialization compatibility on both sides.
- Strict error schema compliance (`error: { code, message, request_id }`).

# Anti-patterns

- ❌ Renaming backend fields without updating client DTOs.
- ❌ Relying on default camelCase-to-snake_case reflection mappers.
- ❌ Exposing internal database column names or provider keys in API payloads.

# Testing requirements

- Test serialization and deserialization of all contract DTOs against sample JSON payloads in `commonTest`.

# Platform considerations

- Client DTOs must be cross-platform compatible (`kotlinx.serialization`).

# Related documentation

- [docs/contracts/api-contract.md](../../docs/contracts/api-contract.md)
