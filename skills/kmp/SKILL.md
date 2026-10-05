---
name: kmp
description: Kotlin Multiplatform core conventions, source set structures, and target management
---

# Purpose
Defines coding, module structure, and build conventions for Kotlin Multiplatform in the Effortless client.

# Scope
`client/` directory, multiplatform source sets (`commonMain`, `androidMain`, `iosMain`, `desktopMain`), expect/actual mechanisms, and Gradle configurations.

# When to use
Use whenever writing shared Kotlin code, declaring multiplatform dependencies, or implementing platform abstractions.

# Architecture rules
- Shared business logic, domain models, repositories, and ViewModels belong in `commonMain`.
- Minimize use of `expect`/`actual`; prefer interface abstractions injected via Koin DI.
- Platform specific code must strictly reside in `androidMain`, `iosMain`, or `desktopMain`.

# Preferred patterns
- Centralized dependency catalog in `gradle/libs.versions.toml`.
- Functional Result types and pure coroutine flows in shared code.
- Clean separation between library module (`:shared`) and platform applications (`:androidApp`, `iosApp`).

# Anti-patterns
- ❌ Leaking Android (`android.*`) or iOS (`platform.*`) packages into `commonMain`.
- ❌ Using platform-specific network engines directly in shared logic.
- ❌ Hardcoding target-specific JVM or binary options in shared modules.

# Testing requirements
- All domain, mapper, and ViewModel logic must be tested in `commonTest`.
- Tests must execute across all target platforms via `./gradlew :shared:allTests`.

# Platform considerations
- Android uses AGP 9 Multiplatform library plugin (`com.android.kotlin.multiplatform.library`).
- iOS compiles to static frameworks (`Shared.framework`).
- Desktop JVM uses Compose Desktop targets.

# Related documentation
- [docs/contracts/api-contract.md](../../docs/contracts/api-contract.md)
