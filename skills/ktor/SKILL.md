---
name: ktor
description: Ktor client networking, platform engine abstraction, and error mapping rules
---

# Purpose
Governs HTTP networking in the Effortless KMP client using Ktor.

# Scope
Ktor HttpClient configuration, ContentNegotiation, platform engines (OkHttp, Darwin, CIO), timeouts, logging, and error handling.

# When to use
Use when creating or updating API data sources, network interceptors, serialization plugins, or WebSocket connections.

# Architecture rules
- Never use platform networking libraries (OkHttp directly, URLSession directly) in shared code.
- Always abstract the HTTP engine via `expect`/`actual createHttpEngine(): HttpClientEngine`.
- The presentation and domain layers must NEVER import Ktor packages (`io.ktor.*`).

# Preferred patterns
- Centralized client construction in `HttpClientFactory`.
- Map all Ktor exceptions (`ClientRequestException`, `ServerResponseException`, `IOException`) into domain `AppError`.
- Use `io.ktor.serialization.kotlinx.json` with lenient JSON parsers.

# Anti-patterns
- ❌ Direct Ktor calls from ViewModels or Composables.
- ❌ Hardcoding engines (e.g. CIO) into `commonMain`.
- ❌ Swallowing network exceptions or logging full authorization tokens.

# Testing requirements
- Use mock engines (`MockEngine`) or repository test doubles (`FakeTranslationRepository`) for unit testing.
- Never make live network calls during automated test suite execution.

# Platform considerations
- Android: OkHttp engine (`io.ktor:ktor-client-okhttp`).
- iOS: Darwin engine (`io.ktor:ktor-client-darwin`).
- Desktop: CIO engine (`io.ktor:ktor-client-cio`).

# Related documentation
- [docs/contracts/api-contract.md](../../docs/contracts/api-contract.md)
