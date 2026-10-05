# Speech Translation API

## POST /v1/speech/translate

Upload audio and receive both a transcript and its translation.

### Request

```
POST /v1/speech/translate
Content-Type: multipart/form-data
X-API-Key: typ_k_abc123
```

Form fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `audio` | file | Yes | Audio file (max 5 MB, max 30 seconds) |
| `source_language` | string | Yes | BCP-47 source language code |
| `target_language` | string | Yes | BCP-47 target language code |

Supported audio formats: WAV, MP3, AAC, FLAC, OGG, OPUS, WebM

### Response

```json
{
  "source_language": "hi-IN",
  "target_language": "en-IN",
  "transcript": "मुझे कल ऑफिस जाना है",
  "translated_text": "I have to go to the office tomorrow.",
  "request_id": "req_abc123"
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `source_language` | string | BCP-47 source language code |
| `target_language` | string | BCP-47 target language code |
| `transcript` | string | Recognized text in source language |
| `translated_text` | string | Translated text in target language |
| `request_id` | string | Unique request identifier |

### Status Codes

| Code | Meaning | Error Code |
|---|---|---|
| `200` | Success | — |
| `400` | Invalid request | `INVALID_LANGUAGE`, `UNSUPPORTED_LANGUAGE_PAIR`, `INVALID_AUDIO`, `AUDIO_TOO_LARGE`, `UNSUPPORTED_AUDIO_FORMAT` |
| `401` | Unauthorized | `AUTHENTICATION_REQUIRED` |
| `429` | Rate limited | `RATE_LIMITED` |
| `500` | Internal error | `SPEECH_RECOGNITION_FAILED`, `TRANSLATION_FAILED`, `INTERNAL_ERROR` |
| `503` | Provider unavailable | `SARVAM_UNAVAILABLE` |

### Validation Rules

1. `audio` file must be provided
2. `audio` file size must not exceed 5 MB
3. `audio` duration must not exceed 30 seconds
4. `audio` format must be one of the supported formats
5. `source_language` and `target_language` must be valid and different
6. The language pair must be supported

### Processing Pipeline

```
1. Validate request (audio format, size, language pair)
2. Send audio to Saaras STT (saaras:v4, mode=transcribe)
3. Receive transcript in source language
4. Send transcript to Translation (Mayura or Sarvam-Translate)
5. Return combined result
```

### Error Examples

```json
// Audio too large (400)
{
  "error": {
    "code": "AUDIO_TOO_LARGE",
    "message": "Audio file exceeds the maximum size of 5 MB.",
    "request_id": "req_005"
  }
}

// Speech recognition failed (500)
{
  "error": {
    "code": "SPEECH_RECOGNITION_FAILED",
    "message": "Unable to recognize speech from the provided audio.",
    "request_id": "req_006"
  }
}
```
