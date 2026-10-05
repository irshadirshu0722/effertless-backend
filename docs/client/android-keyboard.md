# Android Keyboard Architecture

## Overview

The Android Typeless keyboard is implemented as an Input Method Editor (IME) using Android's `InputMethodService`. The AI processing pipeline is decoupled from the keyboard UI.

## Key Components

### InputMethodService

```kotlin
class TypelessIME : InputMethodService() {
    // Lifecycle
    override fun onCreateInputView(): View  // Create keyboard UI
    override fun onStartInput(info: EditorInfo, restarting: Boolean)
    override fun onFinishInput()

    // Text insertion
    private val ic: InputConnection get() = currentInputConnection
    fun insertText(text: String) = ic.commitText(text, 1)
}
```

### Integration Flow

```
Keyboard UI (Compose)
    │
    ├── Language Selector
    │       ├── Source: Hindi
    │       └── Target: English
    │
    ├── Mic Button (tap to speak)
    │       │
    │       ▼
    │   AudioRecorder.start()
    │       │
    │       ▼
    │   RealtimeRepository.connect(src, tgt)
    │       │
    │       ▼
    │   Audio chunks → WebSocket → Backend
    │       │
    │       ▼
    │   Events flow back:
    │       ├── transcript.partial → Show preview text
    │       ├── transcript.final  → Show confirmed text
    │       └── translation.final → Show translated text
    │
    └── Insert Button / Auto-insert
            │
            ▼
        InputConnection.commitText(translatedText, 1)
            │
            ▼
        Text appears in the active app's text field
```

### Audio Capture

```kotlin
// expect/actual in KMP shared module
expect class AudioRecorder {
    fun start(sampleRate: Int = 16000, channels: Int = 1)
    fun stop()
    fun audioChunks(): Flow<ByteArray>
}

// Android actual
actual class AudioRecorder {
    private val audioRecord = AudioRecord(
        MediaRecorder.AudioSource.MIC,
        16000,
        AudioFormat.CHANNEL_IN_MONO,
        AudioFormat.ENCODING_PCM_16BIT,
        bufferSize
    )
    // ... implementation
}
```

### Permissions

- `RECORD_AUDIO` — Required for microphone access
- `INTERNET` — Required for backend communication

### Constraints

- IME runs in a separate process; memory is limited
- Keyboard must remain responsive during AI processing
- Network calls must be async (never block the UI thread)
- Handle configuration changes (rotation, keyboard resize)
- Support Android's IME lifecycle (input start/finish/restart)

### State Management

The `RealtimeViewModel` in KMP shared code manages the state machine:

```
IDLE → CONNECTING → LISTENING → TRANSCRIBING → TRANSLATING → COMPLETED → IDLE
```

The Android keyboard UI observes this state and updates accordingly.
