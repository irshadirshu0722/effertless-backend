# Realtime Translation API

## WS /v1/realtime/translate

WebSocket endpoint for realtime speech-to-translation streaming.

### Connection

```
ws://host/v1/realtime/translate?api_key=typ_k_abc123&source_language=hi-IN&target_language=en-IN
```

| Parameter | Required | Description |
|---|---|---|
| `api_key` | Yes | Client API key |
| `source_language` | Yes | BCP-47 source language code |
| `target_language` | Yes | BCP-47 target language code |

### Connection Lifecycle

1. Client opens WebSocket with query parameters
2. Server validates auth and language pair
3. Server sends `session.created` event
4. Client streams audio as binary frames
5. Server sends transcript and translation events
6. Client sends `session.end` or disconnects
7. Server sends `session.ended` and closes connection

### Client → Server Messages

#### Audio Chunk (Binary)

Send raw audio data as binary WebSocket frames. Recommended format: 16-bit PCM, 16kHz, mono.

#### Session End (JSON)

```json
{
  "type": "session.end"
}
```

### Server → Client Messages

#### session.created

```json
{
  "type": "session.created",
  "session_id": "sess_abc123",
  "source_language": "hi-IN",
  "target_language": "en-IN",
  "created_at": "2026-09-23T18:30:00Z"
}
```

#### transcript.partial

```json
{
  "type": "transcript.partial",
  "session_id": "sess_abc123",
  "text": "मुझे कल ऑफिस",
  "segment_index": 0,
  "is_final": false
}
```

#### transcript.final

```json
{
  "type": "transcript.final",
  "session_id": "sess_abc123",
  "text": "मुझे कल ऑफिस जाना है",
  "segment_index": 0,
  "is_final": true
}
```

#### translation.final

```json
{
  "type": "translation.final",
  "session_id": "sess_abc123",
  "source_text": "मुझे कल ऑफिस जाना है",
  "translated_text": "I have to go to the office tomorrow.",
  "segment_index": 0
}
```

#### error

```json
{
  "type": "error",
  "session_id": "sess_abc123",
  "code": "SPEECH_RECOGNITION_FAILED",
  "message": "Speech recognition encountered an error.",
  "recoverable": true
}
```

#### session.ended

```json
{
  "type": "session.ended",
  "session_id": "sess_abc123",
  "segments_processed": 3,
  "duration_seconds": 12.5
}
```

### Close Codes

| Code | Meaning |
|---|---|
| `1000` | Normal closure |
| `1001` | Client going away |
| `4001` | Authentication failed |
| `4002` | Invalid language pair |
| `4003` | Session timeout |
| `4004` | Rate limited |
| `4010` | Internal server error |

### Constraints

| Constraint | Value |
|---|---|
| Max session duration | 5 minutes |
| Max audio frame size | 64 KB |
| Audio format | 16-bit PCM, 16kHz mono (recommended) |
| Idle timeout | 30 seconds of no audio |

### Client Display Strategy

1. On `transcript.partial`: Show source-language text (preview, may change)
2. On `transcript.final`: Show confirmed source-language text
3. On `translation.final`: Show/replace with target-language text
4. On `error` (recoverable): Show error indicator, continue session
5. On `error` (non-recoverable): Show error, close session
