# Effortless Backend API Contract

This document is the **Single Source of Truth** for the backend network contract and its external consumers.

Any change to endpoints, headers, payloads, or error schemas MUST be reflected here first before altering client or backend code.

---

## 1. Environment & Base URLs

| Environment     | Base URL (Host)                      | Base URL (Android Emulator)          | Base URL (iOS Simulator)             |
| --------------- | ------------------------------------ | ------------------------------------ | ------------------------------------ |
| **Development** | `http://localhost:8000`              | `http://10.0.2.2:8000`               | `http://127.0.0.1:8000`              |
| **Staging**     | `https://staging-api.effortless.app` | `https://staging-api.effortless.app` | `https://staging-api.effortless.app` |
| **Production**  | `https://api.effortless.app`         | `https://api.effortless.app`         | `https://api.effortless.app`         |

---

## 2. Standard Headers

All HTTP requests sent from the client must include:

- `Content-Type: application/json`
- `Accept: application/json`
- `X-Client-Platform: android | ios | desktop`
- `X-Client-Version: <semantic-version>`
- `X-Request-Id: <uuid>` (for distributed tracing)

---

## 3. Endpoints

### 3.1 Health Check (Liveness Probe)

- **Method**: `GET`
- **Path**: `/health`
- **Description**: Verifies service process health without hitting downstream providers.

#### Response `200 OK`

```json
{
  "status": "ok"
}
```

---

### 3.2 Readiness Check

- **Method**: `GET`
- **Path**: `/health/ready`
- **Description**: Verifies configured runtime dependencies needed to serve traffic.

#### Response `200 OK`

```json
{
  "status": "ready",
  "dependencies": {
    "postgres": "connected",
    "redis": "connected"
  }
}
```

#### Response `503 Service Unavailable`

```json
{
  "status": "degraded",
  "dependencies": {
    "postgres": "unreachable",
    "redis": "connected"
  }
}
```

---

### 3.3 Text Translation

- **Method**: `POST`
- **Path**: `/api/v1/translation`
- **Description**: Converts source text into translated target language text.

#### Request Body

```json
{
  "input": "मुझे कल ऑफिस जाना है",
  "source_language_code": "hi-IN",
  "target_language_code": "en-IN"
}
```

| Field                  | Type   | Required | Description                        |
| ---------------------- | ------ | -------- | ---------------------------------- |
| `input`                | String | Yes      | Source text (1 to 2000 characters) |
| `source_language_code` | String | Yes      | BCP-47 language tag (e.g. `hi-IN`) |
| `target_language_code` | String | Yes      | BCP-47 language tag (e.g. `en-IN`) |

#### Response `200 OK`

```json
{
  "translated_text": "I have to go to the office tomorrow.",
  "source_language_code": "hi-IN",
  "target_language_code": "en-IN",
  "request_id": "req-987654"
}
```

---

### 3.4 Speech Translation (Audio Batch)

- **Method**: `POST`
- **Path**: `/api/v1/speech/translate`
- **Content-Type**: `multipart/form-data`
- **Description**: Ephemeral audio ingestion → speech recognition → translation.

#### Request Form Data

- `file`: Binary audio stream (WAV, MP3, AAC, FLAC)
- `source_language_code`: `hi-IN`
- `target_language_code`: `en-IN`

#### Response `200 OK`

```json
{
  "transcript": "मुझे कल ऑफिस जाना है",
  "translated_text": "I have to go to the office tomorrow.",
  "source_language_code": "hi-IN",
  "target_language_code": "en-IN",
  "audio_duration_seconds": 2.4,
  "request_id": "req-123456"
}
```

---

### 3.5 Realtime Voice Streaming (WebSocket)

- **Protocol**: `WebSocket (WSS)`
- **Path**: `/api/v1/realtime/translate`
- **Description**: Bidirectional low-latency audio chunk streaming with translated text emission.

#### Client -> Server Frame: Initial Config

```json
{
  "type": "config",
  "source_language_code": "hi-IN",
  "target_language_code": "en-IN",
  "sample_rate": 16000,
  "encoding": "audio/pcm"
}
```

#### Client -> Server Frame: Binary PCM

- Binary raw PCM frames (16kHz, 16-bit mono, 100ms-200ms per frame).

#### Server -> Client Frame: Incremental Result

```json
{
  "type": "partial",
  "transcript": "मुझे कल",
  "translated_text": ""
}
```

#### Server -> Client Frame: Final Segment

```json
{
  "type": "final",
  "transcript": "मुझे कल ऑफिस जाना है",
  "translated_text": "I have to go to the office tomorrow."
}
```

---

## 4. Standard Error Schema

All `4xx` and `5xx` error responses adhere to this structure:

```json
{
  "error": {
    "code": "INVALID_LANGUAGE_PAIR",
    "message": "Direct translation between en-IN and en-IN is not allowed",
    "request_id": "req-error-789"
  }
}
```

### Standard Error Codes

- `VALIDATION_ERROR` (400)
- `INVALID_LANGUAGE` (400)
- `UNSUPPORTED_LANGUAGE_PAIR` (400)
- `RATE_LIMIT_EXCEEDED` (429)
- `INTERNAL_SERVER_ERROR` (500)
- `PROVIDER_UNAVAILABLE` (503)
