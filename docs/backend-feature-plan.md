# Backend Feature Plan

This plan covers the Python backend repository only. External client applications are out of scope.

## Branch and Commit Convention

Create one short-lived branch per feature:

```text
feature/TN-00{n}-feature-name
```

Use a matching Conventional Commit message:

```text
feat(TN-00{n}): implement feature name
```

Each branch should contain one coherent feature, its documentation changes, and the focused tests for that feature. Do not begin the next branch until the current branch is reviewed and merged.

## Prerequisite Decisions

These decisions must be resolved before endpoint implementation:

1. Select the canonical API prefix: `/v1` or `/api/v1`.
2. Define the GCP Identity Platform bearer-token contract and decide whether legacy API-key authentication remains temporarily supported.
3. Reconcile translation, speech, error, health, and WebSocket payload names across the API documents.
4. Verify current Sarvam endpoints, model names, SDK methods, limits, and realtime behavior from the official documentation before coding provider adapters.
5. Define subscription entities, entitlements, Cashfree webhook events, and the public subscription API.
6. Confirm the published-version compatibility requirements for any existing `/v1` contract.

## Feature Sequence

### 1. Contract Baseline

**Branch:** `feature/TN-001-contract-baseline`

**Commit:** `feat(TN-001): establish backend contract baseline`

Reconcile and update `docs/contracts/api-contract.md` before implementing new endpoints. Standardize route prefixes, authentication transport, request and response field names, error codes, request IDs, health responses, and the WebSocket message protocol. Add a minimal smoke test for the running application and its critical local dependencies.

**Backend work:**

- Align `src/app/api/` route registration and `src/app/schemas/` models with the selected contract.
- Define backward-compatibility rules for published `/v1` endpoints.
- Keep provider-specific fields out of public contracts.
- Add only the smoke coverage needed to confirm the current stack is alive.

**Tests:** schema serialization, OpenAPI paths, response status/error mapping, and WebSocket message compatibility tests.

**Minimal smoke test scope:**

- Start PostgreSQL, Redis, and the FastAPI application through Docker Compose.
- Confirm the application responds to `GET /health` with HTTP 200.
- Confirm `GET /health/ready` reports PostgreSQL and Redis as connected.
- Confirm PostgreSQL accepts a non-mutating connectivity check such as `SELECT 1`.
- Confirm Redis responds to `PING`.
- Fail fast with a useful service-specific message; do not create business data.
- Keep this smoke test separate from unit tests and expand it only when another critical runtime dependency is introduced.

### 2. Backend Foundation

**Branch:** `feature/TN-002-backend-foundation`

**Commit:** `feat(TN-002): establish async backend foundation`

Finalize the async FastAPI application, configuration loading, dependency injection, health endpoints, version routing, request IDs, and centralized error handling.

**Backend work:**

- `src/main.py`
- `src/app/api/`
- `src/app/core/config.py`
- `src/app/core/exceptions.py`
- `src/app/core/logging.py`
- Environment and Docker configuration

**Tests:** app factory, route registration, health/readiness behavior, settings validation, missing-configuration behavior, and the minimal stack smoke test defined above.

### 3. GCP Identity Platform Authentication

**Branch:** `feature/TN-003-gcp-identity-auth`

**Commit:** `feat(TN-003): add identity platform authentication`

Implement backend-only verification of GCP Identity Platform tokens and extraction of the authenticated user identity.

**Backend work:**

- Authentication port in `src/app/ports/`
- GCP adapter in `src/app/adapters/`
- FastAPI dependency wiring in `src/app/api/dependencies.py`
- Security configuration in `src/app/core/`
- Consistent HTTP and WebSocket handshake authentication

Verify current Google documentation before selecting SDK calls, issuer, audience, or token settings. Never put provider credentials in the client or domain layer.

**Tests:** valid, expired, malformed, missing, and revoked-token cases; identity extraction; unauthorized HTTP responses; WebSocket handshake rejection; fake verifier tests without real GCP calls.

### 4. Language Registry

**Branch:** `feature/TN-004-language-registry`

**Commit:** `feat(TN-004): add language registry and capabilities`

Implement immutable language entities/value objects, supported-language registry, capability flags, language-pair validation, and the languages endpoint.

**Backend work:**

- `src/app/domain/entities/`
- `src/app/domain/value_objects/`
- `src/app/domain/languages/`
- `src/app/schemas/`
- `src/app/api/routes/languages.py`

Expose abstract capabilities only. Do not expose Sarvam model names in the domain or public response.

**Tests:** registry lookup/listing, unsupported language errors, same-language rejection, language-pair routing metadata, and API response mapping.

### 5. Sarvam Provider Adapters

**Branch:** `feature/TN-005-sarvam-provider-adapters`

**Commit:** `feat(TN-005): add Sarvam provider adapters`

Implement provider ports, Sarvam speech and translation adapters, response mappers, provider error mapping, and dependency wiring.

**Backend work:**

- Speech and translation ports in `src/app/ports/`
- Sarvam adapters in `src/app/adapters/sarvam/`
- Domain-to-provider and provider-to-domain mappers
- Configuration and API dependency wiring

All external API details must be checked against the latest official Sarvam documentation. Provider SDKs, models, endpoints, and response types must remain outside `src/app/domain/` and `src/app/application/`.

**Tests:** protocol compliance with fakes, mapping, timeout/rate-limit/unavailable errors, credential redaction, and opt-in provider integration tests.

### 6. Text Translation

**Branch:** `feature/TN-006-text-translation`

**Commit:** `feat(TN-006): implement text translation pipeline`

Implement the text translation use case, model routing, direct translation, English-pivot translation, and the HTTP endpoint.

**Backend work:**

- Translation entities/value objects and router in `src/app/domain/`
- Use case in `src/app/application/use_case/`
- Request/response models in `src/app/schemas/`
- Route and dependency wiring in `src/app/api/`

**Tests:** direct translation, router selection, style/model override rules, English-pivot two-step flow, first-hop failure, validation, and API error mapping.

### 7. Speech Translation

**Branch:** `feature/TN-007-speech-translation`

**Commit:** `feat(TN-007): implement speech translation pipeline`

Implement ephemeral audio validation, transcription, translation orchestration, and the combined speech endpoint.

**Backend work:**

- Speech entities and ports in `src/app/domain/` and `src/app/ports/`
- Use case in `src/app/application/use_case/`
- Audio validation and request schemas in `src/app/schemas/` and `src/app/core/`
- Route in `src/app/api/`

Audio must not be persisted or logged. Finalize whether the upload field is `audio` or `file`, supported formats, maximum size, and duration behavior through the contract baseline.

**Tests:** missing/oversized/malformed/unsupported/over-duration audio, fake STT-to-translation flow, provider failures, size limits, and non-persistence assertions.

### 8. Realtime Translation

**Branch:** `feature/TN-008-realtime-translation`

**Commit:** `feat(TN-008): implement realtime translation sessions`

Implement authenticated WebSocket sessions, upstream Sarvam realtime proxying, partial transcript forwarding, final-segment translation, timeouts, backpressure, and cleanup.

**Backend work:**

- Session use case in `src/app/application/use_case/`
- WebSocket schemas and route in `src/app/schemas/` and `src/app/api/`
- Realtime provider adapter in `src/app/adapters/sarvam/`
- Redis-backed transient session/cache state only where required

**Tests:** handshake authentication, state transitions, partial/final events, translation failure, upstream disconnects, frame limits, idle/session timeouts, backpressure, and close codes.

### 9. Cashfree Subscription State

**Branch:** `feature/TN-009-cashfree-subscriptions`

**Commit:** `feat(TN-009): add Cashfree subscription state`

Add the minimal durable subscription projection needed by the application. PostgreSQL is the source of truth; Redis may cache active-subscription reads. Cashfree remains behind an adapter.

**Backend work:**

- Subscription entity/value objects and ports
- PostgreSQL repository adapter and SQLAlchemy models
- Alembic migration
- Cashfree adapter and webhook use case
- Subscription status API and cache invalidation

At minimum, consider `user_id`, `active_subscription`, `updated_at`, and `last_webhook_event_id`. Do not store payment-card data. Define webhook authentication and idempotency before implementation.

**Tests:** repository and migration tests, Cashfree adapter fakes, webhook idempotency, status transitions, cache hit/miss/invalidation, and PostgreSQL-as-source-of-truth behavior.

### 10. Observability, Privacy, and Rate Limits

**Branch:** `feature/TN-010-observability-privacy-hardening`

**Commit:** `feat(TN-010): harden observability and privacy controls`

Add structured logging, request/session correlation, provider latency metrics, safe error responses, rate limits, and privacy enforcement.

**Backend work:**

- `src/app/core/logging.py`
- `src/app/core/exceptions.py`
- Request-ID middleware
- Redis-backed rate limiting and subscription-tier checks
- Provider and WebSocket instrumentation

Never log credentials, raw audio, or sensitive transcripts at normal production levels. Add `Retry-After` for rate-limited HTTP responses.

**Tests:** request-ID propagation, redaction, provider error sanitization, tier-based limits, cache behavior, and health/readiness checks.

### 11. AI Evaluation Gates

**Branch:** `feature/TN-011-ai-evaluation-gates`

**Commit:** `feat(TN-011): add AI pipeline evaluation gates`

Create opt-in evaluation tooling for speech recognition, translation quality, language-pair routing, and English-pivot regressions.

**Backend work:**

- Evaluation runners and fixtures outside the request path
- CI commands and report output
- Regression cases for the supported priority language pairs

Provider calls must be opt-in and excluded from ordinary unit CI. Do not add undocumented providers or future Sarvam models as part of this branch.

**Tests:** WER checks, translation baseline checks, model-router regressions, pivot-path coverage, and deterministic fake-provider tests.

## Working Rules Per Branch

1. Read the relevant docs and current code before editing.
2. State the controlling code path, one falsifiable hypothesis, and one cheap check before the first edit.
3. Keep domain and application layers provider-independent.
4. Add or update unit, integration, adapter-contract, and API tests for every behavior change.
5. Update API contracts and documentation in the same branch when behavior or configuration changes.
6. Do not make real external provider calls in normal CI.
7. Do not commit secrets, raw audio, payment-card data, or sensitive transcripts.
8. Run focused validation before opening the pull request.
9. Use the branch and commit convention defined at the top of this document.
