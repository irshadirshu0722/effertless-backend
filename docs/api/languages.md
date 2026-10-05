# Languages API

## GET /v1/languages

Returns the list of supported languages with their capabilities.

### Request

```
GET /v1/languages
X-API-Key: typ_k_abc123
```

No request body.

### Response

```json
{
  "languages": [
    {
      "code": "en-IN",
      "name": "English",
      "native_name": "English",
      "supports_speech_input": true,
      "supports_translation": true
    },
    {
      "code": "hi-IN",
      "name": "Hindi",
      "native_name": "हिन्दी",
      "supports_speech_input": true,
      "supports_translation": true
    },
    {
      "code": "bn-IN",
      "name": "Bengali",
      "native_name": "বাংলা",
      "supports_speech_input": true,
      "supports_translation": true
    },
    {
      "code": "ta-IN",
      "name": "Tamil",
      "native_name": "தமிழ்",
      "supports_speech_input": true,
      "supports_translation": true
    },
    {
      "code": "ml-IN",
      "name": "Malayalam",
      "native_name": "മലയാളം",
      "supports_speech_input": true,
      "supports_translation": true
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `code` | string | BCP-47 language code |
| `name` | string | English display name |
| `native_name` | string | Name in native script |
| `supports_speech_input` | boolean | Can be used as speech input language |
| `supports_translation` | boolean | Can be used as translation source or target |

### Design Notes

- The response **does not** expose which Sarvam model (Mayura vs. Sarvam-Translate) handles each language
- `supports_translation` is true if the language is supported by ANY translation model
- The client uses this endpoint to populate language picker UI
- The response is cacheable (languages change infrequently)

### Status Codes

| Code | Meaning |
|---|---|
| `200` | Success |
| `401` | Missing or invalid API key |
