---
name: clean-architecture
description: Clean Architecture boundaries, dependency inversion, and layer responsibilities
---

# Purpose
Enforces layer decoupling and dependency inversion across the Effortless application.

# Scope
`domain/`, `data/`, `core/`, and `presentation/` directories.

# When to use
Use whenever adding new features, defining repositories, writing mappers, or creating use cases.

# Architecture rules
- **Dependency Rule**: Source code dependencies must point inward toward the Domain layer.
- `domain/` is pure Kotlin: no Ktor, no Compose, no Android, no iOS, no FastAPI, no Sarvam.
- `data/` implements domain repository interfaces and maps network DTOs into domain entities.
- `presentation/` depends on use cases, never directly on data sources or repositories.

# Preferred patterns
- Repository pattern with interfaces defined in `domain/repository/` and implementations in `data/repository/`.
- Mappers isolated in `data/mapper/` with explicit field transformations.
- Functional `Result<T>` and `AppError` replacing raw exception throwing.

# Anti-patterns
- ❌ Domain models with `@Serializable` or JSON annotations.
- ❌ Using network DTOs directly in ViewModels or Compose UI.
- ❌ Bypassing use cases to call repositories directly from presentation.

# Testing requirements
- Domain logic must be 100% unit-testable without mocking frameworks or emulator runs.

# Platform considerations
- Domain logic compiles identically on JVM, Android, and iOS Native without conditional compilation.

# Related documentation
- [skills/architecture/SKILL.md](../architecture/SKILL.md)
