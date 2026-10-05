# Security Architecture

## Problem

Typeless processes voice data through a backend that holds Sarvam API credentials. The backend must act as the trusted security boundary, protecting both user data and provider credentials.

## Requirements

1. Backend API authentication for all client requests
2. Sarvam API key never exposed to clients
3. Request validation and input size limits
4. Rate limiting per user/device
5. WebSocket authentication
6. No secret leakage in logs or error responses
7. Abuse prevention

## Architecture

### Authentication Flow

```
KMP Client
    │
    │ Authorization: Bearer <client_token>
    ▼
FastAPI Backend
    │
    ├── Validate client token
    ├── Extract user identity
    ├── Check rate limits
    │
    │ API-Subscription-Key: <sarvam_key>  (server-side only)
    ▼
Sarvam AI
```

### Client Authentication (MVP)

For MVP, use API key-based authentication:

```
X-API-Key: <client_api_key>
```

Each registered device/user receives an API key. The backend validates it against a store (initially environment-based, later database-backed).

**Post-MVP**: Migrate to JWT tokens with refresh flow for proper user sessions.

### Request Validation

| Constraint                 | Limit                                | Endpoint                    |
| -------------------------- | ------------------------------------ | --------------------------- |
| Text input length          | 2,000 characters                     | `POST /v1/translation`      |
| Audio file size            | 5 MB                                 | `POST /v1/speech/translate` |
| Audio duration             | 30 seconds (REST)                    | `POST /v1/speech/translate` |
| Audio formats              | WAV, MP3, AAC, FLAC, OGG, OPUS, WebM | All speech endpoints        |
| Language code format       | Valid BCP-47 from registry           | All endpoints               |
| WebSocket message size     | 64 KB per frame                      | `WS /v1/realtime/translate` |
| WebSocket session duration | 5 minutes max                        | `WS /v1/realtime/translate` |

### Rate Limiting

```python
# Tiered rate limits
RATE_LIMITS = {
    "free": {
        "translation": "30/minute",
        "speech": "10/minute",
        "realtime_sessions": "5/hour",
    },
    "pro": {
        "translation": "120/minute",
        "speech": "60/minute",
        "realtime_sessions": "30/hour",
    },
}
```

Implemented via middleware using in-memory counters (MVP) or Redis (production).

### WebSocket Authentication

WebSocket connections are authenticated during the handshake:

```python
@router.websocket("/v1/realtime/translate")
async def realtime_translate(websocket: WebSocket):
    # Extract auth from query params or first message
    token = websocket.query_params.get("token")
    if not await validate_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return
    await websocket.accept()
    # ... proceed with session
```

### Secret Management

| Secret           | Storage              | Access                    |
| ---------------- | -------------------- | ------------------------- |
| `SARVAM_API_KEY` | Environment variable | Backend only              |
| `DATABASE_URL`   | Environment variable | Backend only              |
| Client API keys  | Database (hashed)    | Validated at request time |
| JWT signing key  | Environment variable | Backend only              |

All secrets loaded via Pydantic Settings in `src/app/core/config.py`:

```python
class Settings(BaseSettings):
    sarvam_api_key: str
    sarvam_base_url: str = "https://api.sarvam.ai"
    database_url: str | None = None
    environment: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

### Error Response Safety

Error responses must never contain:

- Stack traces (production)
- Internal file paths
- Database queries
- API keys or tokens
- Provider-specific error details

```python
# Safe error response
{
    "error": {
        "code": "TRANSLATION_FAILED",
        "message": "Translation service is temporarily unavailable. Please try again.",
        "request_id": "req_abc123"
    }
}

# NEVER this:
{
    "error": "SarvamAPIError: 401 Unauthorized - Invalid API key sk-proj-..."
}
```

## Design Decisions

| Decision                            | Rationale                                                         |
| ----------------------------------- | ----------------------------------------------------------------- |
| **API key for MVP**                 | Simplest auth that works; JWT migration planned for user accounts |
| **Server-side Sarvam key**          | Client must never hold provider credentials                       |
| **In-memory rate limiting for MVP** | No Redis dependency; sufficient for initial users                 |
| **Input size limits**               | Prevents abuse and aligns with Sarvam API limits                  |

## Failure Modes

| Failure                | Impact                      | Mitigation                                       |
| ---------------------- | --------------------------- | ------------------------------------------------ |
| Leaked Sarvam API key  | Unauthorized usage, billing | Rotate immediately; key never in source code     |
| Rate limit bypass      | Service abuse               | Defense in depth (client + server limits)        |
| Auth token brute force | Unauthorized access         | Rate limit auth endpoint; use long random tokens |

## Future Evolution

1. **JWT + OAuth**: Proper user authentication with token refresh
2. **Redis rate limiting**: Distributed rate limiting across multiple backend instances
3. **WAF**: Web application firewall for additional protection
4. **Audit logging**: Track all API access for security review
5. **IP allowlisting**: Optional IP restrictions for enterprise deployments
