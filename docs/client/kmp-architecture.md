# KMP Client Architecture

## Overview

The Typeless client is built using Kotlin Multiplatform (KMP) with Compose Multiplatform for UI. The shared module contains all business logic, networking, and data management. Platform-specific code handles audio capture, keyboard integration, and text insertion.

## Shared Module Structure

```
shared/
├── domain/
│   ├── model/
│   │   ├── Language.kt
│   │   ├── LanguagePair.kt
│   │   ├── Transcript.kt
│   │   ├── TranslationResult.kt
│   │   └── RealtimeEvent.kt
│   └── repository/
│       ├── LanguageRepository.kt          # Interface
│       ├── TranslationRepository.kt       # Interface
│       ├── SpeechTranslationRepository.kt # Interface
│       └── RealtimeRepository.kt          # Interface
│
├── data/
│   ├── remote/
│   │   ├── TypelessApi.kt                 # Ktor HTTP client
│   │   ├── TypelessWebSocket.kt           # Ktor WebSocket client
│   │   ├── dto/                           # Data transfer objects
│   │   │   ├── TranslationRequest.kt
│   │   │   ├── TranslationResponse.kt
│   │   │   ├── SpeechTranslationResponse.kt
│   │   │   ├── LanguageResponse.kt
│   │   │   └── RealtimeMessage.kt
│   │   └── mapper/
│   │       └── DtoMapper.kt              # DTO ↔ Domain mapping
│   │
│   └── repository/
│       ├── LanguageRepositoryImpl.kt
│       ├── TranslationRepositoryImpl.kt
│       ├── SpeechTranslationRepositoryImpl.kt
│       └── RealtimeRepositoryImpl.kt
│
├── presentation/
│   ├── state/
│   │   ├── TranslationState.kt           # UI state for translation
│   │   └── RealtimeState.kt              # UI state for realtime (state machine)
│   └── viewmodel/
│       ├── TranslationViewModel.kt
│       └── RealtimeViewModel.kt
│
└── audio/
    └── AudioRecorder.kt                   # Expect/actual for platform audio
```

## Platform-Specific Implementations

```
androidApp/
├── audio/
│   └── AndroidAudioRecorder.kt           # MediaRecorder / AudioRecord
├── keyboard/
│   ├── TypelessIME.kt                    # InputMethodService
│   └── TypelessKeyboardView.kt           # Compose keyboard UI
└── di/
    └── AndroidModule.kt                   # Platform DI

iosApp/
├── audio/
│   └── IOSAudioRecorder.kt              # AVAudioEngine
├── keyboard/
│   └── KeyboardViewController.swift       # UIInputViewController
└── di/
    └── IOSModule.kt                       # Platform DI

desktopApp/
├── audio/
│   └── DesktopAudioRecorder.kt           # javax.sound / platform-specific
├── input/
│   └── TextInsertion.kt                  # Platform text insertion
└── di/
    └── DesktopModule.kt                   # Platform DI
```

## Backend Contract Consumption

The KMP client consumes only the Typeless backend API. It never interacts with Sarvam directly.

### Key Repository Interfaces

```kotlin
interface TranslationRepository {
    suspend fun translate(
        text: String,
        sourceLanguage: String,
        targetLanguage: String,
    ): TranslationResult
}

interface RealtimeRepository {
    fun connect(
        sourceLanguage: String,
        targetLanguage: String,
    ): Flow<RealtimeEvent>

    suspend fun sendAudioChunk(chunk: ByteArray)
    suspend fun endSession()
    suspend fun disconnect()
}

interface LanguageRepository {
    suspend fun getLanguages(): List<Language>
}
```

## Design Principles

1. **Shared business logic**: All non-UI, non-platform code lives in `shared/`
2. **Repository pattern**: Clean abstraction over network calls
3. **State machine in shared code**: Realtime session states managed in KMP, not per-platform
4. **No backend internals**: KMP never sees Sarvam models, error details, or provider-specific data
5. **Offline-aware**: Handle network unavailability gracefully
