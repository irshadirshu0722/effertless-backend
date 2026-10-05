# Architecture Overview

## Problem

Typeless is a cross-platform AI-powered keyboard that converts spoken input in one language into typed text in another language. The system must handle speech recognition, translation, and realtime streaming across Android, iOS, and Desktop — all coordinated through a single backend.

## Requirements

1. **Speech Recognition**: Convert audio input to source-language text using Sarvam Saaras
2. **Translation**: Convert source-language text to target-language text using Sarvam translation models
3. **Realtime Streaming**: Provide low-latency voice-to-translated-text via WebSockets
4. **Platform Independence**: Backend serves Android, iOS, and Desktop identically
5. **Provider Abstraction**: Speech and translation providers are swappable
6. **Latency Optimization**: Minimize time from speech-stop to text-appear
7. **Privacy**: Audio is transient; no persistent storage by default
8. **Scalability Path**: Modular monolith that can scale without rewrite

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        KMP Clients                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Android  │  │   iOS    │  │ Desktop  │                  │
│  │   IME    │  │ Keyboard │  │  Input   │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       │              │              │                        │
│  ┌────┴──────────────┴──────────────┴────┐                  │
│  │         KMP Shared Module             │                  │
│  │  ┌─────────────┐ ┌────────────────┐   │                  │
│  │  │   Domain    │ │   Repository   │   │                  │
│  │  └─────────────┘ └───────┬────────┘   │                  │
│  └──────────────────────────┼────────────┘                  │
└─────────────────────────────┼───────────────────────────────┘
                              │
                    HTTP / WebSocket
                              │
┌─────────────────────────────┼───────────────────────────────┐
│                     FastAPI Backend                          │
│                              │                               │
│  ┌───────────────────────────┴──────────────────────────┐   │
│  │                    API Layer                          │   │
│  │  ┌────────┐ ┌─────────────┐ ┌────────┐ ┌──────────┐ │   │
│  │  │ Health │ │ Translation │ │ Speech │ │ Realtime │ │   │
│  │  └────────┘ └──────┬──────┘ └───┬────┘ └────┬─────┘ │   │
│  └────────────────────┼────────────┼───────────┼────────┘   │
│                       │            │           │             │
│  ┌────────────────────┴────────────┴───────────┴────────┐   │
│  │                Application Layer                      │   │
│  │  ┌──────────────────┐  ┌────────────────────────┐    │   │
│  │  │ TranslateText    │  │ TranslateSpeech        │    │   │
│  │  │ UseCase          │  │ UseCase                │    │   │
│  │  └────────┬─────────┘  └────┬──────────┬────────┘    │   │
│  └───────────┼─────────────────┼──────────┼─────────────┘   │
│              │                 │          │                   │
│  ┌───────────┴─────────────────┴──────────┴─────────────┐   │
│  │                  Domain Layer                         │   │
│  │  ┌──────────┐ ┌────────────┐ ┌────────────────────┐  │   │
│  │  │ Language │ │ Transcript │ │ TranslationResult  │  │   │
│  │  └──────────┘ └────────────┘ └────────────────────┘  │   │
│  │  ┌───────────────────┐  ┌──────────────────────┐     │   │
│  │  │ SpeechProvider    │  │ TranslationProvider  │     │   │
│  │  │ (Protocol)        │  │ (Protocol)           │     │   │
│  │  └────────┬──────────┘  └──────────┬───────────┘     │   │
│  └───────────┼─────────────────────────┼────────────────┘   │
│              │                         │                     │
│  ┌───────────┴─────────────────────────┴────────────────┐   │
│  │              Infrastructure Layer                     │   │
│  │  ┌──────────────────┐  ┌─────────────────────────┐   │   │
│  │  │ SarvamSpeech     │  │ SarvamTranslation       │   │   │
│  │  │ Provider         │  │ Provider                │   │   │
│  │  └────────┬─────────┘  └────────────┬────────────┘   │   │
│  └───────────┼─────────────────────────┼────────────────┘   │
└──────────────┼─────────────────────────┼────────────────────┘
               │                         │
               ▼                         ▼
        ┌──────────────────────────────────────┐
        │           Sarvam AI Platform         │
        │  ┌──────────┐  ┌─────────────────┐   │
        │  │ Saaras   │  │ Mayura /        │   │
        │  │ STT      │  │ Sarvam-Translate│   │
        │  └──────────┘  └─────────────────┘   │
        └──────────────────────────────────────┘
```

## Data Flow

### Text Translation (HTTP)

```
Client POST /v1/translation
    → API Layer validates request, extracts language pair
    → Application Layer: TranslateTextUseCase
        → Domain: validate LanguagePair
        → Domain: select TranslationProvider via TranslationRouter
        → Infrastructure: SarvamTranslationProvider.translate()
        → Domain: map response to TranslationResult
    → API Layer: serialize response
    → Client receives translated text
```

### Speech Translation (HTTP)

```
Client POST /v1/speech/translate (multipart audio)
    → API Layer validates audio + language pair
    → Application Layer: TranslateSpeechUseCase
        → Infrastructure: SarvamSpeechProvider.transcribe(audio)
        → Domain: Transcript created
        → Infrastructure: SarvamTranslationProvider.translate(transcript)
        → Domain: TranslationResult created
    → API Layer: serialize combined response
    → Client receives transcript + translation
```

### Realtime Translation (WebSocket)

```
Client connects to ws://host/v1/realtime/translate
    → Handshake: authenticate, set source/target language
    → Client streams audio chunks
        → Backend forwards to Sarvam Realtime STT
        → Sarvam returns partial/final transcripts
        → On stable segment: trigger translation
        → Backend sends transcript.partial / transcript.final / translation.final events
    → Client disconnects or session ends
```

## Design Decisions

| Decision | Rationale |
|---|---|
| **Decoupled Speech + Translation** | Independent model upgrades, text-only translation support, easier testing |
| **Modular monolith** | Single deployment unit reduces operational complexity for MVP while clean interfaces allow future decomposition |
| **Protocol-based abstraction** | Python Protocols provide structural subtyping without inheritance overhead; works naturally with dependency injection |
| **Sarvam as sole initial provider** | Sarvam provides best Indic language coverage; abstraction layer allows adding providers later |
| **FastAPI with async** | Native async/await, automatic OpenAPI generation, Pydantic integration, WebSocket support |
| **No persistent audio storage** | Privacy by default; audio is ephemeral processing data, not a product feature |

## Alternatives Considered

| Alternative | Why Not Chosen |
|---|---|
| **gRPC instead of REST+WS** | KMP/mobile gRPC tooling is more complex; REST+WS is better supported across platforms |
| **Microservices (separate speech/translation services)** | Over-engineered for MVP; monolith with clean interfaces achieves the same separation |
| **Direct Sarvam SDK in application layer** | Couples business logic to provider; makes testing and provider swaps expensive |
| **GraphQL** | Unnecessary flexibility for well-defined, predictable API surface |
| **Django** | Lacks native async support and built-in OpenAPI; FastAPI is better suited |

## Tradeoffs

- **Monolith vs. microservices**: Faster development but all components share a process. Mitigated by clean layer boundaries.
- **REST for speech upload**: Simpler implementation but limited to 30s audio (Sarvam REST limit). Acceptable because realtime WS handles longer sessions.
- **Indic-to-Indic via English pivot**: Adds latency (~2× translation time) but avoids unsupported direct pairs. Will be revisited when Sarvam adds direct Indic-Indic support.

## Failure Modes

| Failure | Impact | Mitigation |
|---|---|---|
| Sarvam API unavailable | All AI features down | Circuit breaker, error responses, health check monitoring |
| Sarvam rate limited (429) | Requests rejected | Exponential backoff (SDK built-in), usage-based client rate limiting |
| WebSocket disconnect | Realtime session lost | Client reconnection with session resume, state machine handles reconnect |
| Translation model returns low-quality result | Poor UX | AI evaluation framework detects regression, model routing can switch providers |
| Audio too large/long | Request rejected | Client-side validation + backend limits, clear error messages |

## Future Evolution

1. **Multi-provider**: Add Google Translate, Azure, or DeepL as fallback providers behind the same protocol
2. **LLM post-processing**: Sarvam-105B for tone adjustment, grammar correction, contextual rewriting
3. **Edge processing**: On-device speech recognition for reduced latency (Saaras on-device if available)
4. **Caching**: Redis cache for repeated translations of common phrases
5. **Service decomposition**: Extract speech and translation into separate services when scale demands it
6. **Batch processing**: Async job queue for long audio files (Sarvam Batch API)
