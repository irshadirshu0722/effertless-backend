---
name: sarvam-ai
description: Rules and patterns for integrating with the Sarvam AI platform (Saaras, Mayura, Sarvam-Translate)
---

# Sarvam AI Integration Skill

## Purpose

Ensure correct, safe, and maintainable integration with Sarvam AI services.

## When to Use

- Implementing or modifying any Sarvam API integration
- Updating model versions or configuration
- Debugging provider errors
- Adding new language support

## Architectural Principles

1. **Never invent APIs**: Always verify against [docs.sarvam.ai](https://docs.sarvam.ai) before coding
2. **Adapter layer only**: All Sarvam code lives in `src/app/adapters/sarvam/`
3. **Error mapping**: Map all `sarvamai` exceptions to domain exceptions
4. **Model via config**: Model names come from `Settings`, not hardcoded strings
5. **Async client**: Always use `AsyncSarvamAI`, never the sync client

## Rules

- Use `AsyncSarvamAI` from the `sarvamai` package
- Pass `api_subscription_key` from environment config, never hardcoded
- Map all Sarvam responses to domain models via `SarvamMapper`
- Handle rate limits (429) with exponential backoff (SDK handles this, but log it)
- Log provider calls with latency metrics but without request/response content

## Anti-patterns

- ❌ Importing `sarvamai` outside of `src/app/adapters/sarvam/`
- ❌ Returning Sarvam SDK response objects to the application layer
- ❌ Hardcoding model names like `"saaras:v4"` in application code
- ❌ Assuming API parameters without checking docs
- ❌ Logging Sarvam API keys

## Implementation Guidelines

### SDK Client Setup

```python
from sarvamai import AsyncSarvamAI

client = AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)
```

### Speech-to-Text

```python
response = await client.speech_to_text.transcribe(
    file=audio_file,
    model=settings.sarvam_speech_model,  # e.g., "saaras:v4"
    language_code=language.code,          # e.g., "hi-IN" or "auto"
    mode="transcribe",
)
```

### Translation

```python
response = await client.text.translate(
    input=text,
    source_language_code=source.code,
    target_language_code=target.code,
    model=settings.sarvam_translation_model,  # e.g., "mayura:v1"
)
```

## Testing Requirements

- Unit tests use `FakeSpeechProvider` / `FakeTranslationProvider`
- Integration tests with real Sarvam API are marked with `@pytest.mark.sarvam`
- Integration tests require `SARVAM_API_KEY` env var
- Contract tests verify both fake and real providers satisfy the protocol

## Relevant Project Documentation

- [docs/ai/sarvam-model-strategy.md](../../docs/ai/sarvam-model-strategy.md)
- [docs/architecture/provider-abstraction.md](../../docs/architecture/provider-abstraction.md)
- [docs/architecture/language-system.md](../../docs/architecture/language-system.md)

## Examples

```python
# ✅ Correct: Infrastructure layer with error mapping
class SarvamSpeechProvider:
    async def transcribe(self, audio, language, *, mode="transcribe"):
        try:
            response = await self._client.speech_to_text.transcribe(...)
            return SarvamMapper.to_transcript(response, language)
        except Exception as e:
            raise map_sarvam_error(e) from e

# ❌ Wrong: Raw SDK call in use case
class TranslateSpeechUseCase:
    async def execute(self, audio):
        response = await self._sarvam_client.speech_to_text.transcribe(...)  # NO!
```
