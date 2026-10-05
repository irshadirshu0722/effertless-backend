---
name: kotlin
description: Modern Kotlin 2.x standards, coroutines, and serialization rules for Effortless
---

# Purpose
Governs Kotlin language standards, coroutines concurrency, and serialization for shared KMP code.

# Scope
All Kotlin code across `client/` and build scripts.

# When to use
Use when writing asynchronous operations, data models, serialization mappings, or coroutine flows.

# Architecture rules
- Target Kotlin 2.x with explicit typing on public API boundaries.
- Use `kotlinx.coroutines` exclusively for concurrency; never use threads or platform concurrency directly in shared code.
- Use `kotlinx.serialization` with `@Serializable` and `@SerialName` for JSON models. Never use Gson or Moshi.

# Preferred patterns
- Sealed interfaces for domain models and UI states.
- Extension functions for mapping and transformation.
- `StateFlow` and `SharedFlow` with `SharingStarted.WhileSubscribed(5000)` in ViewModels.

# Anti-patterns
- ❌ GlobalScope or unconfined coroutine dispatchers in shared code.
- ❌ Relying on reflection or non-KMP serialization libraries.
- ❌ Blocking thread calls (`runBlocking` or `Thread.sleep`) in UI or coroutine contexts.

# Testing requirements
- Use `kotlinx.coroutines.test.runTest` for all suspending tests.
- Set and reset main dispatchers using `StandardTestDispatcher`.

# Platform considerations
- Kotlin/Native memory model requires strict concurrency safety.
- Platform-specific coroutine dispatchers (Dispatchers.Main, Dispatchers.Default, Dispatchers.IO) must be respected.

# Related documentation
- [skills/kmp/SKILL.md](../kmp/SKILL.md)
