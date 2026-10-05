---
name: compose-multiplatform
description: Compose Multiplatform UI patterns, theme management, and rendering rules
---

# Purpose
Guides UI development across Android, iOS, and Desktop using JetBrains Compose Multiplatform.

# Scope
Declarative `@Composable` UI components, theme definitions, state hoisting, and platform UI interoperability.

# When to use
Use when creating screens, components, animations, or styling in the client application.

# Architecture rules
- Shared UI lives in `commonMain`; do not create platform-specific forks of full screens unless native integration demands it.
- Never place network calls or business logic directly inside `@Composable` functions.
- All state must be hoisted to ViewModels and observed via `collectAsState()`.

# Preferred patterns
- Unidirectional Data Flow with immutable `UiState` and explicit `UiEvent`.
- Material3 themes with dynamic or customized dark/light color schemes.
- Reusable, stateless components with modifiers passed as default arguments.

# Anti-patterns
- ❌ Reading or writing to mutable state outside of StateFlow or remember blocks.
- ❌ Direct dependency on Android-specific Compose extensions in `commonMain`.
- ❌ Hardcoding dimensions, strings, or colors without using tokens or Theme constants.

# Testing requirements
- Verify component rendering and state transitions across screen sizes.
- Test preview compatibility and avoid runtime crashes due to platform-specific APIs.

# Platform considerations
- Compose on iOS uses `ComposeUIViewController`.
- Compose on Desktop uses `application { Window { ... } }`.
- Compose on Android uses `ComponentActivity.setContent { ... }`.

# Related documentation
- [skills/mvvm/SKILL.md](../mvvm/SKILL.md)
