# Scalability Architecture

## Problem

Typeless must support an evolutionary scaling path from 10 users to 100,000+ users without premature infrastructure complexity at the MVP stage.

## Requirements

1. MVP works as a single-process monolith
2. Architecture supports horizontal scaling without redesign
3. Stateless request processing for HTTP endpoints
4. WebSocket state management compatible with multi-instance deployment
5. No premature introduction of distributed systems

## Architecture

### Scaling Stages

```
Stage 1: MVP (10–100 users)
┌─────────────────────────────┐
│   Single FastAPI Process    │
│   (uvicorn, 1 instance)    │
│                             │
│   ┌─────────┐              │
│   │ In-mem  │              │
│   │ rate    │              │
│   │ limit   │              │
│   └─────────┘              │
└─────────────────────────────┘

Stage 2: Growth (100–1,000 users)
┌─────────────────────────────┐
│   Load Balancer             │
│         │                   │
│   ┌─────┴─────┐            │
│   │  FastAPI  │ × N        │
│   │  (gunicorn│            │
│   │   +uvicorn│            │
│   │   workers)│            │
│   └─────┬─────┘            │
│         │                   │
│   ┌─────┴─────┐            │
│   │   Redis   │            │
│   │  (rate    │            │
│   │   limits, │            │
│   │   cache)  │            │
│   └─────┬─────┘            │
│         │                   │
│   ┌─────┴─────┐            │
│   │ PostgreSQL│            │
│   │ (users,   │            │
│   │  usage)   │            │
│   └───────────┘            │
└─────────────────────────────┘

Stage 3: Scale (1,000–10,000 users)
┌─────────────────────────────┐
│   Load Balancer             │
│   (sticky sessions for WS) │
│         │                   │
│   ┌─────┴─────┐            │
│   │  FastAPI  │ × N        │
│   └─────┬─────┘            │
│         │                   │
│   ┌─────┴─────┐            │
│   │   Redis   │            │
│   │  (+ cache │            │
│   │   translations)        │
│   └─────┬─────┘            │
│         │                   │
│   ┌─────┴─────┐            │
│   │ PostgreSQL│            │
│   │ (replicas)│            │
│   └───────────┘            │
└─────────────────────────────┘

Stage 4: High Scale (10,000+ users)
  → Consider: service decomposition, dedicated WS servers,
    translation caching layer, CDN for static assets,
    async job queue for batch operations
```

### Why Modular Monolith

| Benefit | Explanation |
|---|---|
| **Single deployment** | One container, one process, one log stream |
| **Shared memory** | In-process caching, no serialization overhead |
| **Simple debugging** | Full stack trace, no distributed tracing needed |
| **Fast development** | No inter-service communication overhead |
| **Clean interfaces** | Layer boundaries enable future decomposition |

### Stateless Design

HTTP endpoints are fully stateless:

- No server-side session storage
- All request context comes from the request itself
- Auth tokens are self-contained or verified against a store
- Any backend instance can handle any request

WebSocket endpoints have session state (current language pair, Sarvam upstream connection) but this state:
- Lives in memory for the duration of the connection
- Is lost on disconnect (client reconnects and re-establishes)
- Does not need to be shared across instances

### Bottleneck Analysis

| Component | Bottleneck | Mitigation |
|---|---|---|
| **Sarvam STT** | Rate limit (20–100 concurrent WS) | Client-side rate limiting; upgrade Sarvam plan |
| **Sarvam Translation** | Rate limit (60–4000 req/min) | Translation caching; batch requests |
| **Backend CPU** | Minimal (proxying, not computing) | Horizontal scaling |
| **Backend Memory** | WebSocket connections (~1MB each) | Connection limits; horizontal scaling |
| **Network** | Audio upload bandwidth | Client-side compression; OPUS encoding |

### Translation Caching (Stage 2+)

Common phrases can be cached to avoid repeated Sarvam API calls:

```python
# Cache key: (source_text_hash, source_lang, target_lang, model)
# TTL: 24 hours (translations are deterministic for same model version)

cache_key = f"translate:{hash(text)}:{source}:{target}:{model}"
cached = await redis.get(cache_key)
if cached:
    return TranslationResult.from_cache(cached)
```

Conservative estimate: caching common greetings and phrases could reduce translation API calls by 10–20%.

## Design Decisions

| Decision | Rationale |
|---|---|
| **Monolith for MVP** | Fastest path to production; complexity is enemy of shipping |
| **Async FastAPI** | Non-blocking I/O handles many concurrent connections per worker |
| **No Redis at MVP** | In-memory rate limiting is sufficient for 10–100 users |
| **No PostgreSQL at MVP** | Core pipeline is ephemeral; persistence deferred |
| **Sticky sessions for WS** | WebSocket connections must stay on the same backend instance |

## Future Evolution

1. **Redis**: Add when rate limiting needs to be shared across instances
2. **PostgreSQL**: Add when user accounts, usage tracking, or billing is needed
3. **Translation cache**: Add when Sarvam API costs become significant
4. **Service decomposition**: Extract realtime WS into separate service when connection count demands it
5. **Kubernetes**: Deploy when auto-scaling and rolling updates are needed
6. **CDN**: Add when static assets or pre-computed translations benefit from edge caching
