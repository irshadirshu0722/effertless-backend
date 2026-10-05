# API Authentication

## Overview

The Typeless backend uses API key authentication for MVP, with a path to JWT-based authentication for user accounts.

## MVP: API Key Authentication

### Request

Include the API key in the `X-API-Key` header:

```
X-API-Key: typ_k_abc123def456
```

### Key Format

```
typ_k_{32_random_alphanumeric_chars}
```

Prefix `typ_k_` makes keys identifiable in logs and secret scanners.

### Validation

```python
# Backend validates against stored keys
# Keys are stored as SHA-256 hashes (never plaintext)

async def validate_api_key(key: str) -> User | None:
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return await key_store.find_by_hash(key_hash)
```

### Error Responses

```json
// 401 Unauthorized — Missing key
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "API key is required. Include X-API-Key header."
  }
}

// 403 Forbidden — Invalid key
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "The provided API key is invalid or has been revoked."
  }
}
```

## WebSocket Authentication

WebSocket connections pass the API key via query parameter during handshake:

```
ws://host/v1/realtime/translate?api_key=typ_k_abc123def456&source_language=hi-IN&target_language=en-IN
```

Authentication is validated before the WebSocket is accepted. If invalid, the connection is rejected with close code `4001`.

## Future: JWT Authentication

Post-MVP, migrate to JWT tokens for proper user sessions:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Key changes:
- Token issued via login/signup endpoint
- Short-lived access token (15 min) + refresh token (7 days)
- API key still supported for programmatic access

## Backend → Sarvam Authentication

The backend authenticates with Sarvam using a server-side API key:

```
API-Subscription-Key: {SARVAM_API_KEY}
```

This key is **never** sent to or accessible by clients.
