# Backend Architecture

## Problem

The Typeless backend must handle HTTP requests, WebSocket connections, AI provider integration, and business logic orchestration while remaining testable, maintainable, and provider-independent.

## Requirements

1. Clear separation of concerns across architectural layers
2. Dependency injection for all external services
3. Async-first for I/O-bound AI operations
4. Automatic API documentation via OpenAPI
5. Structured error handling with domain-specific error codes
6. Environment-based configuration with no hardcoded secrets

## Architecture

### Project Structure

```
./
├── src/
│   ├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app factory
│   │
│   │   ├── api/                          # API Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py              # Dependency injection providers
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py                # GET /health
│   │       ├── languages.py             # GET /v1/languages
│   │       ├── translation.py           # POST /v1/translation
│   │       ├── speech.py                # POST /v1/speech/translate
│   │       └── realtime.py              # WS /v1/realtime/translate
│   │
│   │   ├── core/                         # Cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── config.py                    # Pydantic Settings
│   │   ├── logging.py                   # Structured logging setup
│   │   ├── security.py                  # Auth middleware, rate limiting
│   │   └── exceptions.py               # Domain exceptions + handlers
│   │
│   │   ├── domain/                       # Domain Layer (pure business logic)
│   │   ├── __init__.py
│   │   ├── languages/
│   │   │   ├── __init__.py
│   │   │   ├── models.py               # Language, LanguagePair
│   │   │   └── registry.py             # Language registry
│   │   ├── speech/
│   │   │   ├── __init__.py
│   │   │   ├── models.py               # Transcript, SpeechSegment
│   │   │   └── providers.py            # SpeechProvider protocol
│   │   └── translation/
│   │       ├── __init__.py
│   │       ├── models.py               # TranslationRequest, TranslationResult
│   │       ├── providers.py            # TranslationProvider protocol
│   │       └── router.py               # TranslationRouter (model selection)
│   │
│   │   ├── application/                 # Application Layer (use cases)
│   │   ├── __init__.py
│   │   ├── translate_text.py            # TranslateTextUseCase
│   │   ├── translate_speech.py          # TranslateSpeechUseCase
│   │   └── realtime_session.py          # RealtimeTranslationSession
│   │
│   │   ├── adapters/                     # External provider adapters
│   │   ├── drivers/                      # Database and cache drivers
│   │   ├── __init__.py
│   │   └── sarvam/
│   │       ├── __init__.py
│   │       ├── client.py                # SarvamAI client wrapper
│   │       ├── speech_provider.py       # SarvamSpeechProvider
│   │       ├── translation_provider.py  # SarvamTranslationProvider
│   │       ├── mapper.py                # Sarvam ↔ Domain model mapping
│   │       └── errors.py               # Sarvam error → domain error mapping
│   │
│   │   ├── schemas/                      # API request/response schemas
│   │   └── ports/                        # Application-facing abstractions
│       ├── __init__.py
│       ├── common.py                    # ErrorResponse, Pagination
│       ├── languages.py                 # LanguageResponse
│       ├── translation.py              # TranslationRequest/Response
│       ├── speech.py                    # SpeechTranslationResponse
│       └── realtime.py                  # WebSocket message schemas
│
│   ├── migrations/                       # Alembic migrations
│   └── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Shared fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── test_language_registry.py
│   │   │   ├── test_translation_router.py
│   │   │   └── test_models.py
│   │   └── application/
│   │       ├── test_translate_text.py
│   │       └── test_translate_speech.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── sarvam/
│   │       ├── test_speech_provider.py
│   │       └── test_translation_provider.py
│   └── api/
│       ├── __init__.py
│       ├── test_health.py
│       ├── test_translation.py
│       ├── test_speech.py
│       └── test_realtime.py
│
├── docs/                                # Architecture & API docs
├── skills/                              # Agent skill definitions
├── scripts/                             # Development & deployment scripts
│
├── .env.example                         # Environment variable template
├── .gitignore
├── pyproject.toml                       # Project config, dependencies
├── Dockerfile
└── README.md
```

### Layer Responsibilities

#### API Layer (`src/app/api/`)

- HTTP route handlers and WebSocket endpoints
- Request validation (via Pydantic schemas)
- Response serialization
- Authentication and authorization checks
- HTTP status code selection
- No business logic

```python
# Example: translation route handler
@router.post("/v1/translation", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    use_case: TranslateTextUseCase = Depends(get_translate_text_use_case),
) -> TranslationResponse:
    result = await use_case.execute(
        text=request.text,
        source_language=request.source_language,
        target_language=request.target_language,
    )
    return TranslationResponse.from_domain(result)
```

#### Application Layer (`src/app/application/`)

- Use case orchestration
- Coordinates domain objects and infrastructure services
- Transaction boundaries (when database is added)
- No HTTP/WebSocket awareness
- No direct provider SDK calls

```python
# Example: use case
class TranslateSpeechUseCase:
    def __init__(
        self,
        speech_provider: SpeechProvider,
        translation_provider: TranslationProvider,
        language_registry: LanguageRegistry,
    ):
        self._speech = speech_provider
        self._translation = translation_provider
        self._languages = language_registry

    async def execute(
        self, audio: bytes, source_language: str, target_language: str
    ) -> SpeechTranslationResult:
        pair = self._languages.validate_pair(source_language, target_language)
        transcript = await self._speech.transcribe(audio, pair.source)
        translation = await self._translation.translate(
            transcript.text, pair.source, pair.target
        )
        return SpeechTranslationResult(transcript=transcript, translation=translation)
```

#### Domain Layer (`src/app/domain/`)

- Pure business logic and domain models
- Protocol definitions for providers
- Language registry and validation
- No framework imports (no FastAPI, no Pydantic for internal models)
- No infrastructure dependencies
- Dataclasses or plain Python objects

#### Adapters and Drivers (`src/app/adapters/` and `src/app/drivers/`)

- Concrete implementations of domain protocols
- Sarvam SDK integration
- Database repositories (when added)
- Cache clients (when added)
- Maps external data to/from domain models

### Dependency Injection

FastAPI's `Depends()` system provides dependency injection without a framework:

```python
# src/app/api/dependencies.py

from functools import lru_cache

def get_settings() -> Settings:
    return Settings()

def get_sarvam_client(settings: Settings = Depends(get_settings)) -> AsyncSarvamAI:
    return AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)

def get_speech_provider(client = Depends(get_sarvam_client)) -> SpeechProvider:
    return SarvamSpeechProvider(client)

def get_translation_provider(client = Depends(get_sarvam_client)) -> TranslationProvider:
    return SarvamTranslationProvider(client)

def get_translate_text_use_case(
    translation: TranslationProvider = Depends(get_translation_provider),
    registry: LanguageRegistry = Depends(get_language_registry),
) -> TranslateTextUseCase:
    return TranslateTextUseCase(translation, registry)
```

## Design Decisions

| Decision                                | Rationale                                                                                     |
| --------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Flat application layer**              | Use cases are few and focused; sub-packages add overhead without value at MVP scale           |
| **Protocols over ABCs**                 | Structural subtyping avoids inheritance; test doubles don't need to inherit from a base class |
| **Separate schemas from domain models** | API schemas (Pydantic) handle serialization; domain models remain framework-free              |
| **No ORM yet**                          | PostgreSQL is deferred until persistence requirements are concrete                            |
| **`lru_cache` for singletons**          | Simple singleton pattern for settings and shared clients without a DI container               |

## Alternatives Considered

| Alternative                                   | Why Not Chosen                                                                                                                                            |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Dependency Injector library**               | FastAPI's built-in `Depends` is sufficient; adding a DI framework is premature                                                                            |
| **Hexagonal architecture (ports & adapters)** | Conceptually similar to our layered approach but the terminology and file structure conventions add complexity without proportional benefit at this scale |
| **Single `services/` package**                | Conflates orchestration (use cases) with domain logic; layered separation is clearer                                                                      |

## Tradeoffs

- **More files/packages**: The layered structure creates more files than a flat FastAPI app. Acceptable because each file has a single responsibility and the project will grow.
- **Protocol duplication**: Provider protocols may mirror SDK interfaces. Acceptable because it decouples the domain from the SDK.

## Failure Modes

| Failure                         | Impact                  | Mitigation                                                                 |
| ------------------------------- | ----------------------- | -------------------------------------------------------------------------- |
| Circular imports between layers | Build failure           | Enforce layer dependency rule: API → Application → Domain ← Infrastructure |
| DI misconfiguration             | Runtime NoneType errors | Integration tests that exercise the full DI chain                          |
| Schema/domain model drift       | Serialization bugs      | Explicit `from_domain()` / `to_domain()` mapping methods with tests        |

## Future Evolution

1. **Database layer**: Add SQLAlchemy async repositories under `src/app/drivers/`
2. **Cache layer**: Add Redis adapters under `src/app/adapters/`
3. **Background tasks**: Add Celery or ARQ for long-running batch operations
4. **Multi-provider**: Add provider adapters under `src/app/adapters/`
