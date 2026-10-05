---
name: koin
description: Dependency injection architecture and module definitions using Koin Multiplatform
---

# Purpose
Governs dependency injection across all platforms in the Effortless client.

# Scope
Koin modules (`networkModule`, `repositoryModule`, `useCaseModule`, `viewModelModule`), scope bindings, and Compose integration.

# When to use
Use when registering new services, repositories, use cases, ViewModels, or platform-specific drivers.

# Architecture rules
- Centralize all DI declarations in `core/di/AppModule.kt`.
- Use constructor injection exclusively for repositories and use cases.
- ViewModels are injected using `koinViewModel()` in Compose.

# Preferred patterns
- Modular DI splits (`networkModule`, `repositoryModule`, `useCaseModule`, `viewModelModule`).
- Single source of entry via `KoinApplication { modules(appModules) }` in `App.kt`.
- Seamless swapping of production implementations with test doubles (`FakeTranslationRepository`).

# Anti-patterns
- ❌ Calling `get()` or using Koin as a manual service locator in business logic.
- ❌ Injecting Android `Context` into domain or data layer singletons.
- ❌ Circular dependencies between modules.

# Testing requirements
- Verify module definitions with Koin module verification rules where applicable.
- In tests, supply mocked or fake dependencies directly via class constructors without initializing Koin.

# Platform considerations
- Compose Multiplatform integrates via `koin-compose` and `koin-compose-viewmodel`.

# Related documentation
- [skills/clean-architecture/SKILL.md](../clean-architecture/SKILL.md)
