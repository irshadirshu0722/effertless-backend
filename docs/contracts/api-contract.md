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

Protected endpoints must also include:

- `Authorization: Bearer <gcp_identity_platform_id_token>`

System endpoints `/health` and `/health/ready` are public.

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

### 3.6 Subscriptions

#### 3.6.1 List Public Plans
- **Method**: `GET`
- **Path**: `/api/v1/subscriptions/plans`
- **Description**: Returns all currently active subscription plans and pricing.

##### Response `200 OK`
```json
{
  "plans": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "code": "lite_monthly",
      "name": "Lite",
      "billing_period": "monthly",
      "actual_price": 499.00,
      "offer_price": 299.00,
      "currency": "INR",
      "max_seconds_per_request": 30,
      "max_usage_per_day": 50
    }
  ]
}
```

---

#### 3.6.2 Current User Subscription & Quota
- **Method**: `GET`
- **Path**: `/api/v1/subscriptions/me`
- **Headers**: `Authorization: Bearer <token>`
- **Description**: Returns user's active subscription tier, limits, and today's usage balance.

##### Response `200 OK`
```json
{
  "status": "active",
  "plan_name": "Lite",
  "current_period_end": "2026-11-09T00:00:00Z",
  "limits": {
    "max_seconds_per_request": 30,
    "max_usage_per_day": 50
  },
  "usage_today": {
    "used": 12,
    "limit": 50,
    "remaining": 38
  }
}
```

---

#### 3.6.3 Create Checkout Session
- **Method**: `POST`
- **Path**: `/api/v1/subscriptions/checkout`
- **Headers**: `Authorization: Bearer <token>`
- **Description**: Initiates a Cashfree subscription checkout session.

##### Request Body
```json
{
  "plan_code": "lite_monthly",
  "return_url": "https://effortless.app/subscription/success"
}
```

##### Response `200 OK`
```json
{
  "subscription_id": "sub_cf_12345",
  "payment_link": "https://payments.cashfree.com/sub/...",
  "status": "pending"
}
```

---

#### 3.6.4 Cashfree Webhook Handler
- **Method**: `POST`
- **Path**: `/api/v1/subscriptions/webhook`
- **Headers**:
  - `x-webhook-signature: <signature>`
  - `x-webhook-timestamp: <timestamp>`
- **Description**: Idempotent processing of Cashfree subscription events.

##### Response `200 OK`
```json
{
  "status": "acknowledged"
}
```

---

#### 3.6.5 Cancel Subscription
- **Method**: `POST`
- **Path**: `/api/v1/subscriptions/cancel`
- **Headers**: `Authorization: Bearer <token>`
- **Description**: Cancels auto-renewal for the user's active subscription.

##### Response `200 OK`
```json
{
  "status": "cancelled",
  "current_period_end": "2026-11-09T00:00:00Z"
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

- `AUTHENTICATION_REQUIRED` (401)
- `INVALID_AUTH_TOKEN` (401)
- `AUTH_TOKEN_REVOKED` (401)
- `AUTHORIZATION_FAILED` (403)
- `VALIDATION_ERROR` (400)
- `INVALID_LANGUAGE` (400)
- `UNSUPPORTED_LANGUAGE_PAIR` (400)
- `AUDIO_EXCEEDS_TIER_LIMIT` (400)
- `SUBSCRIPTION_REQUIRED` (402)
- `DAILY_QUOTA_EXCEEDED` (429)
- `RATE_LIMIT_EXCEEDED` (429)
- `PLAN_NOT_FOUND` (404)
- `INVALID_WEBHOOK_SIGNATURE` (401)
- `INTERNAL_SERVER_ERROR` (500)
- `PROVIDER_UNAVAILABLE` (503)

