# Observability Architecture

## Problem

Typeless is an AI-driven product where the critical user experience metric — time from speech-stop to translated text appearing — spans multiple services and network hops. Effective observability is required to debug latency issues, track quality, and operate the system reliably.

## Requirements

1. Structured logging with request correlation
2. Per-stage latency measurement
3. End-to-end latency tracking (the primary product metric)
4. Error rate monitoring per provider and model
5. WebSocket connection metrics
6. No sensitive data in logs or metrics

## Architecture

### Structured Logging

All log entries use JSON format in production with consistent fields:

```python
import structlog

logger = structlog.get_logger()

# Every log entry includes:
logger.info(
    "event_description",
    request_id="req_abc123",          # Unique per HTTP request or WS session
    user_id="usr_xyz789",             # Authenticated user (if available)
    session_id="sess_def456",         # WebSocket session (if applicable)
    provider="sarvam",                # External service involved
    model="mayura:v1",                # AI model used
    source_language="hi-IN",
    target_language="en-IN",
    latency_ms=234,
    status="success",                 # success | error
    error_code=None,                  # Domain error code (if error)
)
```

### Latency Tracking

The primary product metric:

```
┌─────────────────────────────────────────────────────────────────────┐
│          End-to-End Latency (speech-stop → text-appear)            │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Network  │  │ Speech   │  │ Translate │  │ Network  │           │
│  │ Upload   │  │ Recog.   │  │           │  │ Download │           │
│  │          │  │ (Saaras) │  │ (Mayura)  │  │          │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                     │
│  Client-side    Backend-measurable latency      Client-side         │
└─────────────────────────────────────────────────────────────────────┘
```

Backend-measurable stages:

```python
@dataclass
class RequestMetrics:
    """Latency metrics for a single request."""

    request_id: str
    timestamp: datetime

    # Speech recognition
    speech_start_ms: float | None = None
    speech_end_ms: float | None = None
    speech_model: str | None = None

    # Translation
    translation_start_ms: float | None = None
    translation_end_ms: float | None = None
    translation_model: str | None = None
    pivot_used: bool = False

    # Computed
    @property
    def speech_latency_ms(self) -> float | None:
        if self.speech_start_ms and self.speech_end_ms:
            return self.speech_end_ms - self.speech_start_ms
        return None

    @property
    def translation_latency_ms(self) -> float | None:
        if self.translation_start_ms and self.translation_end_ms:
            return self.translation_end_ms - self.translation_start_ms
        return None

    @property
    def total_backend_latency_ms(self) -> float | None:
        stages = [self.speech_latency_ms, self.translation_latency_ms]
        valid = [s for s in stages if s is not None]
        return sum(valid) if valid else None
```

### Key Metrics

| Metric                     | Type      | Description                                  |
| -------------------------- | --------- | -------------------------------------------- |
| `speech_latency_ms`        | Histogram | Saaras STT processing time                   |
| `translation_latency_ms`   | Histogram | Translation processing time                  |
| `total_backend_latency_ms` | Histogram | Total backend processing time                |
| `pivot_translation_count`  | Counter   | Number of Indic-to-Indic pivot translations  |
| `request_count`            | Counter   | Total requests by endpoint, status           |
| `error_count`              | Counter   | Errors by error code, provider               |
| `provider_error_rate`      | Gauge     | Error rate per provider (rolling window)     |
| `ws_connection_duration_s` | Histogram | WebSocket session duration                   |
| `ws_active_connections`    | Gauge     | Currently active WebSocket connections       |
| `ws_segments_per_session`  | Histogram | Number of translated segments per WS session |

### Request ID Correlation

Every request gets a unique ID that flows through all log entries:

```python
# src/app/core/logging.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        # Bind to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### Health Check

```python
# GET /health
{
    "status": "healthy",
    "version": "0.1.0",
    "checks": {
        "sarvam_api": "reachable",       # Periodic ping
        "database": "not_configured"      # MVP: no database
    }
}
```

## Design Decisions

| Decision                               | Rationale                                                            |
| -------------------------------------- | -------------------------------------------------------------------- |
| **structlog**                          | Structured, context-aware logging; JSON output for production        |
| **Middleware-based request ID**        | Consistent correlation without manual threading                      |
| **Histogram for latencies**            | Percentile analysis (p50, p95, p99) for SLO tracking                 |
| **No external metrics system for MVP** | Structured logs can be queried; Prometheus/Grafana added when needed |

## Tradeoffs

- **Log-based metrics for MVP**: Slower to query than dedicated metrics system, but zero additional infrastructure.
- **No distributed tracing for MVP**: Single monolith doesn't need trace propagation; add OpenTelemetry when services split.

## Future Evolution

1. **Prometheus + Grafana**: Dedicated metrics collection and dashboarding
2. **OpenTelemetry**: Distributed tracing across backend and Sarvam calls
3. **Alerting**: PagerDuty/Slack alerts on error rate spikes or latency degradation
4. **SLOs**: Define and track service level objectives (e.g., p95 < 500ms)
5. **Client-side metrics**: KMP client reports network latency and text insertion timing
