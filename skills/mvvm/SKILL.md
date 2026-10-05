---
name: mvvm
description: Model-View-ViewModel and Unidirectional Data Flow architecture patterns
---

# Purpose
Guides state management, presentation logic, and UI event processing.

# Scope
ViewModels, UI States, UI Events, UI Effects, and Compose screen bindings.

# When to use
Use when creating or updating UI screens, handling user interactions, or exposing state to Compose.

# Architecture rules
- Every screen is backed by a dedicated `ViewModel` extending `androidx.lifecycle.ViewModel`.
- UI State is exposed as an immutable `StateFlow<UiState>`.
- UI Events are submitted to the ViewModel via a single `onEvent(event: UiEvent)` method.

# Preferred patterns
- Unidirectional Data Flow (UDF): User Action → Event → ViewModel → Use Case → State Update → Compose Recomposition.
- Encapsulate multiple related fields in a single data class (`HomeUiState`).
- Keep ViewModels free of Android framework classes (`Context`, `View`, `Bundle`).

# Anti-patterns
- ❌ Multiple separate `StateFlow` primitives for a single screen when one coherent state object is cleaner.
- ❌ Direct mutation of state from `@Composable` UI.
- ❌ Putting business or validation logic in the UI layer.

# Testing requirements
- ViewModels must be thoroughly unit tested with `runTest` and `StandardTestDispatcher`.
- Verify all event transitions (e.g. `TranslateClicked` toggles loading, updates result).

# Platform considerations
- `androidx.lifecycle:lifecycle-viewmodel-compose` runs seamlessly across Android, iOS, and Desktop.

# Related documentation
- [skills/compose-multiplatform/SKILL.md](../compose-multiplatform/SKILL.md)
