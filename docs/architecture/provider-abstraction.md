# Provider Abstraction Architecture

## Problem

The backend must interact with external AI services (Sarvam) for speech recognition and translation. These integrations must be swappable, testable, and isolated from business logic.

## Requirements

1. Business logic never imports provider SDKs directly
2. Test doubles (mocks/fakes) must be trivially substitutable
3. Provider-specific errors must be mapped to domain errors
4. Multiple translation providers must coexist (Mayura, Sarvam-Translate)
5. Adding a new provider must not require changing application or domain code

## Architecture

### Protocol Definitions

```python
# src/app/domain/speech/providers.py
from typing import Protocol
from app.domain.speech.models import Transcript, AudioInput
from app.domain.languages.models import Language

class SpeechProvider(Protocol):
    """Protocol for speech-to-text providers."""

    async def transcribe(
        self,
        audio: AudioInput,
        language: Language,
        *,
        mode: str = "transcribe",
    ) -> Transcript:
        """Transcribe audio to text in the specified language.

        Args:
            audio: Raw audio data with format metadata
            language: Expected language of the audio
            mode: Transcription mode (transcribe, translate, verbatim, translit, codemix)

        Returns:
            Transcript with recognized text

        Raises:
            SpeechRecognitionError: When transcription fails
        """
        ...
```

```python
# src/app/domain/translation/providers.py
from typing import Protocol
from app.domain.translation.models import TranslationResult
from app.domain.languages.models import Language

class TranslationProvider(Protocol):
    """Protocol for text translation providers."""

    async def translate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
    ) -> TranslationResult:
        """Translate text from source to target language.

        Args:
            text: Source text to translate
            source_language: Language of the input text
            target_language: Desired output language

        Returns:
            TranslationResult with translated text

        Raises:
            TranslationError: When translation fails
            UnsupportedLanguagePairError: When the pair is not supported
        """
        ...
```

### Sarvam Implementations

```python
# src/app/adapters/sarvam/speech_provider.py
from sarvamai import AsyncSarvamAI
from app.domain.speech.providers import SpeechProvider
from app.domain.speech.models import Transcript, AudioInput
from app.domain.languages.models import Language
from app.infrastructure.sarvam.mapper import SarvamMapper
from app.infrastructure.sarvam.errors import map_sarvam_error

class SarvamSpeechProvider:
    """Sarvam Saaras implementation of SpeechProvider."""

    def __init__(self, client: AsyncSarvamAI, model: str = "saaras:v4"):
        self._client = client
        self._model = model

    async def transcribe(
        self,
        audio: AudioInput,
        language: Language,
        *,
        mode: str = "transcribe",
    ) -> Transcript:
        try:
            response = await self._client.speech_to_text.transcribe(
                file=audio.to_file(),
                model=self._model,
                language_code=language.code,
                mode=mode,
            )
            return SarvamMapper.to_transcript(response, language)
        except Exception as e:
            raise map_sarvam_error(e) from e
```

```python
# src/app/adapters/sarvam/translation_provider.py
from sarvamai import AsyncSarvamAI
from app.domain.translation.providers import TranslationProvider
from app.domain.translation.models import TranslationResult
from app.domain.languages.models import Language
from app.infrastructure.sarvam.mapper import SarvamMapper
from app.infrastructure.sarvam.errors import map_sarvam_error

class SarvamMayuraProvider:
    """Sarvam Mayura implementation of TranslationProvider."""

    def __init__(self, client: AsyncSarvamAI):
        self._client = client
        self._model = "mayura:v1"

    async def translate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
    ) -> TranslationResult:
        try:
            response = await self._client.text.translate(
                input=text,
                source_language_code=source_language.code,
                target_language_code=target_language.code,
                model=self._model,
            )
            return SarvamMapper.to_translation_result(response, source_language, target_language)
        except Exception as e:
            raise map_sarvam_error(e) from e


class SarvamTranslateProvider:
    """Sarvam-Translate implementation of TranslationProvider."""

    def __init__(self, client: AsyncSarvamAI):
        self._client = client
        self._model = "sarvam-translate:v1"

    async def translate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
    ) -> TranslationResult:
        try:
            response = await self._client.text.translate(
                input=text,
                source_language_code=source_language.code,
                target_language_code=target_language.code,
                model=self._model,
            )
            return SarvamMapper.to_translation_result(response, source_language, target_language)
        except Exception as e:
            raise map_sarvam_error(e) from e
```

### Mock/Fake Providers

```python
# tests/fakes/speech_provider.py
class FakeSpeechProvider:
    """Deterministic fake for unit testing."""

    def __init__(self, transcript_text: str = "मुझे कल ऑफिस जाना है"):
        self._transcript_text = transcript_text
        self.call_count = 0

    async def transcribe(self, audio, language, *, mode="transcribe"):
        self.call_count += 1
        return Transcript(text=self._transcript_text, language=language, confidence=0.95)


class FakeTranslationProvider:
    """Deterministic fake for unit testing."""

    def __init__(self, translated_text: str = "I have to go to the office tomorrow."):
        self._translated_text = translated_text
        self.call_count = 0

    async def translate(self, text, source_language, target_language):
        self.call_count += 1
        return TranslationResult(
            source_text=text,
            translated_text=self._translated_text,
            source_language=source_language,
            target_language=target_language,
        )
```

### Error Mapping

```python
# src/app/adapters/sarvam/errors.py
from app.core.exceptions import (
    SpeechRecognitionError,
    TranslationError,
    ProviderRateLimitedError,
    ProviderUnavailableError,
    ProviderTimeoutError,
)

def map_sarvam_error(error: Exception) -> Exception:
    """Map Sarvam SDK exceptions to domain exceptions."""
    error_type = type(error).__name__

    if "RateLimitError" in error_type or "429" in str(error):
        return ProviderRateLimitedError("Sarvam API rate limit exceeded", provider="sarvam")

    if "APIConnectionError" in error_type:
        return ProviderUnavailableError("Sarvam API is unreachable", provider="sarvam")

    if "APITimeoutError" in error_type:
        return ProviderTimeoutError("Sarvam API request timed out", provider="sarvam")

    if "APIStatusError" in error_type:
        return TranslationError(f"Sarvam API returned an error: {error}", provider="sarvam")

    return TranslationError(f"Unexpected Sarvam error: {error}", provider="sarvam")
```

### Dependency Graph

```
Application Layer
    │
    ├── depends on ──▶ SpeechProvider (Protocol)
    │                       │
    │                       ├── SarvamSpeechProvider (production)
    │                       └── FakeSpeechProvider (tests)
    │
    └── depends on ──▶ TranslationProvider (Protocol)
                            │
                            ├── SarvamMayuraProvider (production)
                            ├── SarvamTranslateProvider (production)
                            └── FakeTranslationProvider (tests)
```

## Design Decisions

| Decision                                           | Rationale                                             |
| -------------------------------------------------- | ----------------------------------------------------- |
| **Protocol over ABC**                              | Structural subtyping; fakes don't need inheritance    |
| **Separate Mayura and Sarvam-Translate providers** | Different capabilities, limits, and optimal use cases |
| **Error mapping at infrastructure boundary**       | Domain layer never sees `sarvamai` exceptions         |
| **Mapper class**                                   | Centralizes Sarvam response → domain model conversion |

## Alternatives Considered

| Alternative                                           | Why Not Chosen                                                                    |
| ----------------------------------------------------- | --------------------------------------------------------------------------------- |
| **ABC with registration**                             | Requires inheritance; Protocols are more Pythonic                                 |
| **Single SarvamTranslationProvider with model param** | Hides the fundamental difference between Mayura and Sarvam-Translate capabilities |
| **Generic provider factory**                          | Over-engineering for two providers; can be added if more providers are introduced |

## Tradeoffs

- **Two translation provider classes** with similar code: Some duplication, but each can evolve independently (different params, limits, error handling).
- **Protocol methods are minimal**: Only `transcribe` and `translate`. More methods can be added but each must be implemented by all providers including fakes.

## Failure Modes

| Failure                                   | Impact                          | Mitigation                                                       |
| ----------------------------------------- | ------------------------------- | ---------------------------------------------------------------- |
| Provider SDK breaks on upgrade            | All calls fail                  | Pin SDK version; integration tests catch breaking changes        |
| Error mapping misses new error type       | Unhandled exception surfaces    | Catch-all in error mapper; structured logging for unknown errors |
| Fake provider diverges from real behavior | Tests pass but production fails | Contract tests validate both real and fake providers             |

## Future Evolution

1. Add `GoogleSpeechProvider`, `AzureTranslationProvider` behind same protocols
2. Add `CachedTranslationProvider` decorator for Redis caching
3. Add `FallbackTranslationProvider` that tries primary then secondary
4. Add streaming protocol method for realtime providers
