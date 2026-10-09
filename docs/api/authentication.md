# API Authentication

## Overview

Effortless uses GCP Identity Platform ID tokens for client authentication.
Clients authenticate with GCP Identity Platform, then send the resulting ID token
to the Effortless backend. The backend verifies tokens server-side and extracts a
provider-independent user identity for application code.

Do not send Sarvam, Cashfree, database, or other provider credentials to clients.

## HTTP Authentication

All protected HTTP endpoints use the standard bearer-token header:

```http
Authorization: Bearer <gcp_identity_platform_id_token>
```

System health endpoints remain public:

- `GET /health`
- `GET /health/ready`

Feature endpoints under `/api/v1` require authentication unless explicitly
documented otherwise.

## WebSocket Authentication

WebSocket endpoints must authenticate during the opening handshake, before the
connection is accepted.

Preferred transport:

```http
Authorization: Bearer <gcp_identity_platform_id_token>
```

Fallback transport for clients that cannot set WebSocket headers:

```text
wss://host/api/v1/realtime/translate?access_token=<gcp_identity_platform_id_token>
```

If authentication fails, the backend rejects or closes the connection with close
code `4001`.

## Backend Verification

The backend verifies ID tokens using the official Google/Firebase Admin SDK for
GCP Identity Platform-compatible tokens.

Verification must:

- validate token signature and issuer
- validate the configured GCP project audience
- reject expired, malformed, revoked, or disabled-user tokens
- return only provider-independent identity data to domain/application code
- avoid logging raw tokens or token claims containing sensitive data

## Authenticated Identity

Application code receives an authenticated identity with this logical shape:

```json
{
  "user_id": "provider-stable-subject",
  "email": "user@example.com",
  "email_verified": true
}
```

Only `user_id` is required. Email fields are optional because not every client
or account provider guarantees them.

## Error Responses

Missing token:

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication is required. Include an Authorization: Bearer token.",
    "request_id": "req_abc123"
  }
}
```

Invalid, expired, or malformed token:

```json
{
  "error": {
    "code": "INVALID_AUTH_TOKEN",
    "message": "The authentication token is invalid or expired.",
    "request_id": "req_abc123"
  }
}
```

Revoked token:

```json
{
  "error": {
    "code": "AUTH_TOKEN_REVOKED",
    "message": "The authentication token has been revoked.",
    "request_id": "req_abc123"
  }
}
```

Valid identity without required authorization:

```json
{
  "error": {
    "code": "AUTHORIZATION_FAILED",
    "message": "The authenticated user is not allowed to perform this action.",
    "request_id": "req_abc123"
  }
}
```

## Backend to Sarvam Authentication

The backend authenticates with Sarvam using a server-side API key loaded from
environment configuration. This key is never sent to or accessible by clients.
