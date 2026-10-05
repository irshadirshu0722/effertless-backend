# Translation API

## POST /v1/translation

Translate text from a source language to a target language.

### Request

```
POST /v1/translation
Content-Type: application/json
X-API-Key: typ_k_abc123
```

```json
{
  "text": "मुझे कल ऑफिस जाना है",
  "source_language": "hi-IN",
  "target_language": "en-IN"
}
```

### Request Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | Yes | Text to translate (max 2,000 characters) |
| `source_language` | string | Yes | BCP-47 source language code |
| `target_language` | string | Yes | BCP-47 target language code |

### Response

```json
{
  "source_language": "hi-IN",
  "target_language": "en-IN",
  "source_text": "मुझे कल ऑफिस जाना है",
  "translated_text": "I have to go to the office tomorrow.",
  "request_id": "req_abc123"
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `source_language` | string | BCP-47 source language code |
| `target_language` | string | BCP-47 target language code |
| `source_text` | string | Original input text |
| `translated_text` | string | Translated output text |
| `request_id` | string | Unique request identifier for debugging |

### Status Codes

| Code | Meaning | Error Code |
|---|---|---|
| `200` | Success | — |
| `400` | Invalid request | `INVALID_LANGUAGE`, `UNSUPPORTED_LANGUAGE_PAIR`, `TEXT_TOO_LONG` |
| `401` | Unauthorized | `AUTHENTICATION_REQUIRED` |
| `429` | Rate limited | `RATE_LIMITED` |
| `500` | Internal error | `TRANSLATION_FAILED`, `INTERNAL_ERROR` |
| `503` | Provider unavailable | `SARVAM_UNAVAILABLE` |

### Validation Rules

1. `text` must not be empty
2. `text` must not exceed 2,000 characters
3. `source_language` must be a valid code from the language registry
4. `target_language` must be a valid code from the language registry
5. `source_language` and `target_language` must differ
6. The language pair must be supported for translation

### Examples

#### Hindi → English

```json
// Request
{ "text": "आज मौसम बहुत अच्छा है", "source_language": "hi-IN", "target_language": "en-IN" }

// Response
{
  "source_language": "hi-IN",
  "target_language": "en-IN",
  "source_text": "आज मौसम बहुत अच्छा है",
  "translated_text": "The weather is very good today.",
  "request_id": "req_001"
}
```

#### English → Malayalam

```json
// Request
{ "text": "Good morning, how are you?", "source_language": "en-IN", "target_language": "ml-IN" }

// Response
{
  "source_language": "en-IN",
  "target_language": "ml-IN",
  "source_text": "Good morning, how are you?",
  "translated_text": "സുപ്രഭാതം, സുഖമാണോ?",
  "request_id": "req_002"
}
```

#### Error — Unsupported Language Pair

```json
// Request
{ "text": "Hello", "source_language": "en-IN", "target_language": "fr-FR" }

// Response (400)
{
  "error": {
    "code": "UNSUPPORTED_LANGUAGE_PAIR",
    "message": "Translation from en-IN to fr-FR is not currently supported.",
    "request_id": "req_003"
  }
}
```
