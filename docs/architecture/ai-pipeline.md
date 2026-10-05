# AI Pipeline Architecture

## Problem

Typeless must convert spoken input in one language to written text in another language. This requires coordinating two distinct AI capabilities — speech recognition and translation — while optimizing for latency, quality, and provider independence.

## Requirements

1. Speech and translation must be independently upgradeable
2. Different translation models for different use cases (colloquial vs. formal)
3. Support for arbitrary language pairs (not just Hindi→English)
4. Latency tracking at each pipeline stage
5. Graceful degradation when a provider is unavailable
6. Text-only translation without speech input

## Architecture

### Core Pipeline

```
Audio Input
    │
    ▼
┌─────────────────────┐
│   SpeechProvider     │
│   (Saaras v4)        │
│                      │
│   audio → transcript │
└──────────┬──────────┘
           │
           ▼
    Source-language
      Transcript
           │
           ▼
┌─────────────────────────┐
│   TranslationRouter     │
│                          │
│   ┌───────────────────┐  │
│   │ Model Selection   │  │
│   │ Logic             │  │
│   └────────┬──────────┘  │
│            │              │
│   ┌────────┴────────┐    │
│   ▼                 ▼    │
│ Mayura v1    Sarvam-     │
│ (colloquial) Translate   │
│              v1 (formal) │
└──────────┬──────────────┘
           │
           ▼
    Target-language
      Translation
```

### Translation Router

The `TranslationRouter` selects the appropriate translation model based on:

1. **Language pair**: Mayura supports 10 languages; Sarvam-Translate supports 22
2. **Configuration**: Explicit model override via settings
3. **Translation style**: Colloquial (Mayura) vs. formal (Sarvam-Translate)

```python
class TranslationRouter:
    """Selects the appropriate translation provider based on language pair and configuration."""

    def __init__(
        self,
        mayura: TranslationProvider,
        sarvam_translate: TranslationProvider,
        config: TranslationConfig,
    ):
        self._mayura = mayura
        self._sarvam_translate = sarvam_translate
        self._config = config

    def select_provider(
        self, source: Language, target: Language, style: TranslationStyle = TranslationStyle.COLLOQUIAL
    ) -> TranslationProvider:
        # Explicit config override
        if self._config.force_model:
            return self._get_provider(self._config.force_model)

        # Mayura is preferred for its 10 supported languages (better colloquial quality)
        if self._is_mayura_supported(source, target) and style != TranslationStyle.FORMAL:
            return self._mayura

        # Fall back to Sarvam-Translate for broader coverage or formal style
        return self._sarvam_translate
```

### Model Selection Matrix

| Source → Target | Mayura | Sarvam-Translate | Recommended |
|---|---|---|---|
| Hindi → English | ✅ | ✅ | Mayura (colloquial quality) |
| English → Hindi | ✅ | ✅ | Mayura (colloquial quality) |
| Tamil → English | ✅ | ✅ | Mayura (colloquial quality) |
| Malayalam → Hindi | ❌ direct | ❌ direct | Sarvam-Translate via English pivot |
| Assamese → English | ❌ | ✅ | Sarvam-Translate |
| Sanskrit → Hindi | ❌ | ❌ direct | Sarvam-Translate via English pivot |

### Indic-to-Indic Pivot Strategy

Neither Mayura nor Sarvam-Translate directly supports Indic-to-Indic translation. The pipeline handles this via English pivot:

```
Hindi → Malayalam (not directly supported)

Step 1: Hindi → English (Mayura or Sarvam-Translate)
Step 2: English → Malayalam (Mayura or Sarvam-Translate)

Total: 2 translation calls
```

This is handled transparently by the `TranslateSpeechUseCase`:

```python
async def _translate_with_pivot(
    self, text: str, source: Language, target: Language
) -> TranslationResult:
    if self._can_translate_direct(source, target):
        return await self._translate_direct(text, source, target)

    # Pivot via English
    english = self._languages.get("en-IN")
    intermediate = await self._translate_direct(text, source, english)
    return await self._translate_direct(intermediate.translated_text, english, target)
```

### Saaras `translate` Mode Optimization

Saaras v4 has a built-in `translate` mode that produces English text directly from speech, bypassing the need for a separate translation call for `X→English` pairs:

```
Standard pipeline:  Audio → Saaras(transcribe) → Hindi text → Mayura → English text
Optimized pipeline: Audio → Saaras(translate)  → English text directly
```

This optimization is implemented as a pipeline strategy:

```python
class PipelineStrategy(Enum):
    STANDARD = "standard"      # Always: STT → Translate (decoupled)
    OPTIMIZED = "optimized"    # Use Saaras translate mode when target=English

# Default: STANDARD (for consistent behavior and debugging)
# Can be switched to OPTIMIZED via configuration for latency-sensitive deployments
```

> **Decision**: The STANDARD pipeline is the default because it:
> - Produces a source-language transcript (useful for the client to display)
> - Allows translation quality to be independently evaluated
> - Keeps the pipeline consistent regardless of target language
>
> The OPTIMIZED path is available as a configuration option for when latency is critical and the source transcript is not needed.

## Data Flow

### Stage Latency Tracking

Every pipeline execution records timing at each stage:

```python
@dataclass
class PipelineMetrics:
    request_id: str
    speech_start_ms: float
    speech_end_ms: float
    speech_duration_ms: float      # Saaras processing time
    translation_start_ms: float
    translation_end_ms: float
    translation_duration_ms: float  # Translation processing time
    total_duration_ms: float        # End-to-end backend time
    model_speech: str               # e.g., "saaras:v4"
    model_translation: str          # e.g., "mayura:v1"
    pivot_used: bool                # Whether English pivot was needed
```

## Design Decisions

| Decision | Rationale |
|---|---|
| **Mayura as default for supported pairs** | Better colloquial/code-mixed quality for conversational keyboard input |
| **Configuration-driven model selection** | Allows A/B testing and gradual rollout of new models |
| **STANDARD pipeline as default** | Predictable behavior; source transcript is valuable for UX |
| **Transparent pivot** | Clients don't need to know about the English intermediate step |

## Alternatives Considered

| Alternative | Why Not Chosen |
|---|---|
| **Single translation model** | Would sacrifice either quality (Mayura's 10 languages) or coverage (Sarvam-Translate's 22) |
| **Client-side model selection** | Leaks provider details; backend should abstract this |
| **Always use Saaras translate mode for English targets** | Loses source transcript; harder to debug and evaluate |
| **Direct Indic-Indic model** | Not available from Sarvam; pivot is the recommended approach |

## Tradeoffs

- **Pivot latency**: Indic-to-Indic adds ~2× translation time. Acceptable for correctness; latency can be optimized with caching.
- **Two translation models**: More complexity in routing but better quality per language.
- **Source transcript in STANDARD mode**: Extra Saaras call for English targets, but provides valuable debugging and UX data.

## Failure Modes

| Failure | Impact | Mitigation |
|---|---|---|
| Saaras fails | No transcript | Return `SPEECH_RECOGNITION_FAILED` error |
| Mayura fails but Sarvam-Translate available | Degraded quality | Router falls back to Sarvam-Translate |
| Pivot first hop fails | No translation | Return `TRANSLATION_FAILED`; don't attempt second hop |
| Both translation models fail | No translation | Return `TRANSLATION_FAILED` with provider details in logs |

## Future Evolution

1. **LLM post-processing**: Add Sarvam-105B after translation for tone/grammar refinement
2. **Model A/B testing**: Route percentage of traffic to different models, compare quality metrics
3. **Direct Indic-Indic**: When Sarvam adds support, remove pivot for supported pairs
4. **Caching**: Cache common translations (e.g., greetings, common phrases) to skip translation call
5. **On-device STT**: Use on-device Saaras (if available) to reduce network latency
