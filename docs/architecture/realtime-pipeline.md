# Realtime Pipeline Architecture

## Problem

Typeless's core UX is realtime: the user speaks and translated text appears as they talk. This requires streaming audio to the backend, processing it through speech recognition and translation in near-real-time, and streaming results back to the client — all over a persistent WebSocket connection.

## Requirements

1. Sub-second latency from speech to partial transcript display
2. Segment-aware translation (don't translate every partial token)
3. Stable WebSocket connection with graceful error handling
4. Support for connection lifecycle (connect, stream, pause, resume, disconnect)
5. Authentication on WebSocket connection
6. Session state management
7. Backpressure handling for slow clients

## Architecture

### WebSocket Protocol

```
Client                          Backend                         Sarvam Realtime
  │                                │                                │
  │──── WS Connect ───────────────▶│                                │
  │     (auth token, src_lang,     │                                │
  │      tgt_lang in query/header) │                                │
  │                                │                                │
  │◀─── session.created ──────────│                                │
  │     {session_id, config}       │                                │
  │                                │──── WS Connect ──────────────▶│
  │                                │     (API key, model, lang)     │
  │                                │                                │
  │──── audio.chunk ──────────────▶│──── audio chunk ─────────────▶│
  │     (binary frame)             │     (binary forward)           │
  │                                │                                │
  │                                │◀─── partial transcript ───────│
  │◀─── transcript.partial ───────│                                │
  │     {text, is_final: false}    │                                │
  │                                │                                │
  │──── audio.chunk ──────────────▶│──── audio chunk ─────────────▶│
  │                                │                                │
  │                                │◀─── final transcript ─────────│
  │◀─── transcript.final ────────│                                │
  │     {text, is_final: true}     │                                │
  │                                │                                │
  │                                │── translate(final_text) ──────▶│ (REST)
  │                                │◀─ translation result ─────────│
  │                                │                                │
  │◀─── translation.final ───────│                                │
  │     {source, translated}       │                                │
  │                                │                                │
  │──── session.end ──────────────▶│──── close ───────────────────▶│
  │◀─── session.ended ───────────│                                │
  │                                │                                │
```

### Message Types

#### Client → Backend

| Type | Format | Description |
|---|---|---|
| `audio.chunk` | Binary frame | Raw audio data (PCM/WAV/OPUS) |
| `session.configure` | JSON | Update session config mid-stream |
| `session.end` | JSON | Gracefully end the session |

#### Backend → Client

| Type | Format | Description |
|---|---|---|
| `session.created` | JSON | Session initialized, ready for audio |
| `transcript.partial` | JSON | Interim transcript (may change) |
| `transcript.final` | JSON | Stable transcript for a segment |
| `translation.final` | JSON | Translation of a final transcript segment |
| `error` | JSON | Error event |
| `session.ended` | JSON | Session cleanup complete |

### Message Schemas

```json
// session.created
{
  "type": "session.created",
  "session_id": "sess_abc123",
  "source_language": "hi-IN",
  "target_language": "en-IN",
  "created_at": "2026-09-23T18:30:00Z"
}

// transcript.partial
{
  "type": "transcript.partial",
  "session_id": "sess_abc123",
  "text": "मुझे कल ऑफिस",
  "segment_index": 0,
  "is_final": false
}

// transcript.final
{
  "type": "transcript.final",
  "session_id": "sess_abc123",
  "text": "मुझे कल ऑफिस जाना है",
  "segment_index": 0,
  "is_final": true
}

// translation.final
{
  "type": "translation.final",
  "session_id": "sess_abc123",
  "source_text": "मुझे कल ऑफिस जाना है",
  "translated_text": "I have to go to the office tomorrow.",
  "segment_index": 0
}

// error
{
  "type": "error",
  "session_id": "sess_abc123",
  "code": "SPEECH_RECOGNITION_FAILED",
  "message": "Speech recognition encountered an error.",
  "recoverable": true
}
```

### Translation Timing Strategy

**Problem**: Translating every partial transcript is wasteful and produces poor results because partials are incomplete thoughts.

**Strategy**: Only translate **final** transcript segments.

```
Timeline:
  Audio streaming ──────────────────────────────▶

  Sarvam partials:
    "मुझे"  →  "मुझे कल"  →  "मुझे कल ऑफिस"  →  "मुझे कल ऑफिस जाना"

  Sarvam final:
                                                    "मुझे कल ऑफिस जाना है"
                                                              │
                                                              ▼
                                                      Translation call
                                                              │
                                                              ▼
                                                    "I have to go to the
                                                     office tomorrow."
```

**Client display strategy**:
1. Show partial transcripts in source language as user speaks (provides feedback)
2. When final transcript arrives, show it in source language
3. When translation arrives, replace/append with target language text

### State Machine

```
                    ┌──────────┐
                    │   IDLE   │
                    └────┬─────┘
                         │ client connects
                         ▼
                    ┌──────────────┐
                    │ CONNECTING   │
                    └────┬────┬────┘
                         │    │ connection failed
                    success   ▼
                         │  ┌───────┐
                         │  │ ERROR │──── retry ────▶ CONNECTING
                         │  └───┬───┘
                         │      │ max retries
                         │      ▼
                         │  ┌──────┐
                         │  │ IDLE │
                         │  └──────┘
                         ▼
                    ┌──────────────┐
                    │  LISTENING   │◀──────────────────────┐
                    └────┬────┬────┘                       │
                         │    │ client cancels             │
                    audio │   ▼                            │
                    chunk │ ┌───────────┐                  │
                         │ │ CANCELLED │──▶ IDLE           │
                         │ └───────────┘                  │
                         ▼                                 │
                    ┌───────────────┐                      │
                    │ TRANSCRIBING  │                      │
                    │ (partial)     │──── more audio ──────┘
                    └────┬─────────┘
                         │ final segment
                         ▼
                    ┌──────────────┐
                    │ TRANSLATING  │
                    └────┬─────────┘
                         │ translation complete
                         ▼
                    ┌──────────────┐
                    │  COMPLETED   │──── new segment ──▶ LISTENING
                    └────┬─────────┘
                         │ session ends
                         ▼
                    ┌──────────┐
                    │   IDLE   │
                    └──────────┘
```

> **Note**: TRANSCRIBING and LISTENING can overlap — the client may continue sending audio while partials are being processed. The state machine is primarily for the backend session's logical state.

### Connection Lifecycle

1. **Connect**: Client opens WebSocket with auth token and language pair
2. **Validate**: Backend validates auth and language pair
3. **Initialize**: Backend opens upstream connection to Sarvam Realtime API
4. **Stream**: Client sends audio; backend proxies to Sarvam and forwards results
5. **Segment Boundary**: On final transcript, trigger translation
6. **End**: Client sends `session.end` or disconnects; backend closes upstream connection

### Connection Parameters

```
ws://host/v1/realtime/translate?source_language=hi-IN&target_language=en-IN&token=<auth_token>
```

Or via headers:
```
Authorization: Bearer <token>
X-Source-Language: hi-IN
X-Target-Language: en-IN
```

## Data Flow

```
Client audio chunk (binary)
    │
    ▼
FastAPI WebSocket handler
    │
    ├── Validate session state
    │
    ├── Forward audio to Sarvam Realtime WS
    │       │
    │       ▼
    │   Sarvam processes audio
    │       │
    │       ├── Partial transcript → send transcript.partial to client
    │       │
    │       └── Final transcript
    │               │
    │               ├── Send transcript.final to client
    │               │
    │               └── Trigger translation (async)
    │                       │
    │                       ▼
    │                   Sarvam Translation API (REST)
    │                       │
    │                       ▼
    │                   Send translation.final to client
    │
    └── Handle errors, disconnects, timeouts
```

## Design Decisions

| Decision | Rationale |
|---|---|
| **Translate only final segments** | Partials are unstable and produce garbage translations; finals are complete thoughts |
| **Sarvam Realtime API** | Provides true partial transcripts, VAD, and low-latency processing |
| **REST for translation** | Translation is a single synchronous call; WebSocket adds unnecessary complexity |
| **Session-based model** | Each WS connection = one translation session with fixed language pair |
| **Binary frames for audio** | Avoids base64 encoding overhead; WebSocket natively supports binary |

## Alternatives Considered

| Alternative | Why Not Chosen |
|---|---|
| **Translate every partial** | Wasteful, poor quality, high cost, and introduces flicker |
| **Client-side batching** | Moves complexity to all platforms (Android/iOS/Desktop); backend is the right place |
| **Server-Sent Events** | Unidirectional; can't receive audio chunks |
| **gRPC streaming** | More complex client setup; WebSocket is universally supported |

## Tradeoffs

- **Final-only translation** means the user sees source-language partials until the sentence completes, then sees the translation. This is a deliberate UX choice — instant partial translations would be incoherent.
- **Single WS connection** per session simplifies state management but means reconnection drops all partial state.

## Failure Modes

| Failure | Impact | Mitigation |
|---|---|---|
| Sarvam Realtime WS drops | No transcription | Reconnect upstream; send `error` event to client |
| Client disconnects mid-stream | Orphaned upstream connection | Timeout-based cleanup; close Sarvam WS |
| Translation call fails after final transcript | Transcript delivered but no translation | Send `error` event; client shows transcript only |
| Audio format unsupported | No processing | Validate early; send `error` with `UNSUPPORTED_AUDIO_FORMAT` |
| Backpressure (client can't consume fast enough) | Message queue grows | Drop old partials; always deliver finals and translations |

## Future Evolution

1. **Speculative translation**: Translate partials when they look "stable enough" (e.g., haven't changed for 500ms)
2. **Multi-segment pipelining**: Translate segment N while transcribing segment N+1
3. **Session resume**: Allow reconnection with session ID to resume from last final segment
4. **Adaptive VAD**: Tune silence detection based on language and speaking patterns
5. **On-device STT**: Reduce latency by running Saaras on-device, only sending text to backend for translation
