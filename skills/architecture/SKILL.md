---
name: architecture
description: Global system architecture and monorepo coordination rules for Effortless
---

# Purpose

Governs the Python FastAPI backend architecture in this repository and its external API consumers.

# Scope

Monorepo layout, domain decoupling, cross-project dependencies, and service boundaries.

# When to use

Use when modifying top-level repository structures, introducing new service modules, or evaluating system integration points.

# Architecture rules

- This repository contains the Effortless backend at the repository root, with application code under `src/app/`.
- Domain models in both backend and client must remain pure and free of external platform/framework dependencies.
- External clients NEVER call Sarvam AI or cloud speech APIs directly; all requests route through this backend.
- The backend never embeds platform-specific logic (no Android/iOS branching).

# Preferred patterns

- Clean Architecture with Domain, Data, Presentation layers.
- Contract-first API development documented in `docs/contracts/`.
- Provider abstractions behind Protocols (Python) and Interfaces (Kotlin).

# Anti-patterns

- ❌ Direct communication between client and Sarvam AI.
- ❌ Committing secrets or environment files.
- ❌ Introducing microservices or distributed queues prematurely.

# Testing requirements

- Backend tests live under `src/tests/`.
- Continuous contract validation between client DTOs and backend Pydantic models.

# Platform considerations

- Shared business logic resides in `commonMain`; platform runners (`androidApp`, `iosApp`, `desktopMain`) remain lightweight wrappers.

# Related documentation

- [docs/contracts/api-contract.md](../../docs/contracts/api-contract.md)
- [AGENTS.md](../../AGENTS.md)
