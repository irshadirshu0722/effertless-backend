---
name: kmp-integration
description: Guidelines for designing backend APIs that integrate cleanly with KMP clients
---

# KMP Integration Skill

## Purpose

Ensure the backend API is designed for clean consumption by Kotlin Multiplatform clients across Android, iOS, and Desktop.

## When to Use

- Designing new API endpoints or response schemas
- Making changes to existing API contracts
- Considering platform-specific needs
- Reviewing API backward compatibility

## Architectural Principles

1. **Platform-independent responses**: No Android/iOS/Desktop specific data
2. **Clean DTOs**: Response shapes map directly to Kotlin data classes
3. **No provider leakage**: Clients never see Sarvam model names or provider errors
4. **Backward compatible**: Deployed apps can't be force-updated
5. **WebSocket events are typed**: Each event has a `type` field for Kotlin sealed class mapping

## Rules

- Response field names use `snake_case` (standard JSON; Kotlin serialization handles mapping)
- Language codes use BCP-47 format consistently
- Error responses always include `code` and `message` for client-side handling
- New response fields are always optional/additive
- WebSocket message `type` field is the discriminator for sealed class deserialization

## Anti-patterns

- ❌ Returning FastAPI internal error format (Pydantic validation errors as-is)
- ❌ Platform-specific response fields (`android_deep_link`, `ios_bundle_id`)
- ❌ Changing response field types between versions
- ❌ Removing response fields without versioning

## Implementation Guidelines

### KMP-Friendly Response Design

```json
// ✅ Good: Simple, flat, typed
{
  "source_language": "hi-IN",
  "target_language": "en-IN",
  "translated_text": "Hello"
}

// ❌ Bad: Nested provider details
{
  "result": {
    "sarvam_response": { ... },
    "provider": "mayura",
    "internal_model_version": "v1.2.3"
  }
}
```

### KMP Sealed Class Mapping

```kotlin
// WebSocket events map to sealed class
sealed class RealtimeEvent {
    data class TranscriptPartial(val text: String, val segmentIndex: Int) : RealtimeEvent()
    data class TranscriptFinal(val text: String, val segmentIndex: Int) : RealtimeEvent()
    data class TranslationFinal(val sourceText: String, val translatedText: String) : RealtimeEvent()
    data class Error(val code: String, val message: String, val recoverable: Boolean) : RealtimeEvent()
}
```

## Relevant Project Documentation

- [docs/client/kmp-architecture.md](../../docs/client/kmp-architecture.md)
- [docs/api/overview.md](../../docs/api/overview.md)
- [docs/api/versioning.md](../../docs/api/versioning.md)
