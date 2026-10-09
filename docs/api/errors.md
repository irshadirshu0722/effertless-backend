# Error Handling

## Error Response Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description.",
    "request_id": "req_abc123"
  }
}
```

## Error Codes

### Client Errors (4xx)

| Code                        | HTTP Status | Description                                     |
| --------------------------- | ----------- | ----------------------------------------------- |
| `AUTHENTICATION_REQUIRED`   | 401         | No bearer token provided                        |
| `INVALID_AUTH_TOKEN`        | 401         | Bearer token is invalid, expired, or malformed  |
| `AUTH_TOKEN_REVOKED`        | 401         | Bearer token has been revoked                   |
| `AUTHORIZATION_FAILED`      | 403         | User is authenticated but not allowed           |
| `INVALID_LANGUAGE`          | 400         | Language code is not recognized                 |
| `UNSUPPORTED_LANGUAGE_PAIR` | 400         | The source→target combination is not supported  |
| `TEXT_TOO_LONG`             | 400         | Input text exceeds maximum length (2,000 chars) |
| `TEXT_EMPTY`                | 400         | Input text is empty                             |
| `INVALID_AUDIO`             | 400         | Audio data is malformed or unreadable           |
| `AUDIO_TOO_LARGE`           | 400         | Audio file exceeds maximum size (5 MB)          |
| `UNSUPPORTED_AUDIO_FORMAT`  | 400         | Audio format is not supported                   |
| `RATE_LIMITED`              | 429         | Too many requests; retry after indicated delay  |
| `VALIDATION_ERROR`          | 422         | Request body failed validation (Pydantic)       |

### Server Errors (5xx)

| Code                        | HTTP Status | Description                            |
| --------------------------- | ----------- | -------------------------------------- |
| `SPEECH_RECOGNITION_FAILED` | 500         | Saaras failed to process the audio     |
| `TRANSLATION_FAILED`        | 500         | Translation model failed               |
| `SARVAM_RATE_LIMITED`       | 503         | Backend hit Sarvam API rate limits     |
| `SARVAM_UNAVAILABLE`        | 503         | Sarvam API is unreachable              |
| `REQUEST_TIMEOUT`           | 504         | Request timed out waiting for provider |
| `INTERNAL_ERROR`            | 500         | Unexpected internal error              |

### WebSocket Errors

| Code                        | Recoverable | Description                                     |
| --------------------------- | ----------- | ----------------------------------------------- |
| `SPEECH_RECOGNITION_FAILED` | Yes         | STT error for a segment; can continue with next |
| `TRANSLATION_FAILED`        | Yes         | Translation error; transcript still valid       |
| `SESSION_TIMEOUT`           | No          | Session exceeded maximum duration               |
| `AUTHENTICATION_REQUIRED`   | No          | No bearer token provided during handshake       |
| `INVALID_AUTH_TOKEN`        | No          | Handshake token is invalid, expired, or revoked |
| `PROVIDER_DISCONNECTED`     | No          | Upstream provider connection lost               |
| `CLIENT_DISCONNECTED`       | No          | Client connection lost (logged server-side)     |

## Error Handling Principles

1. **Never expose provider details**: Error messages must not contain Sarvam API errors, model names, or internal URLs
2. **Always include request_id**: For debugging and support correlation
3. **Distinguish recoverable from non-recoverable**: WebSocket errors indicate whether the session can continue
4. **Rate limit headers**: Include `Retry-After` header on 429 responses
5. **No stack traces in production**: Internal errors return generic message

## Implementation

```python
# src/app/core/exceptions.py
from dataclasses import dataclass

@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int = 500

class InvalidLanguageError(AppError):
    def __init__(self, language_code: str):
        super().__init__(
            code="INVALID_LANGUAGE",
            message=f"Language code '{language_code}' is not recognized.",
            status_code=400,
        )

class UnsupportedLanguagePairError(AppError):
    def __init__(self, source: str, target: str):
        super().__init__(
            code="UNSUPPORTED_LANGUAGE_PAIR",
            message=f"Translation from {source} to {target} is not currently supported.",
            status_code=400,
        )

# FastAPI exception handler
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )
```
