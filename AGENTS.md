# Effortless — Agent Rules

This document defines the mandatory rules that any AI agent or engineer working on the Effortless codebase must follow.

These rules are non-negotiable. Violation of any rule must be flagged and corrected before merging.

---

## Effortless Engineering Rules

### Git

- Never work directly on `main`.
- One branch per logical feature/fix (`feature/*`, `fix/*`, `chore/*`).
- Keep branches short-lived.
- Delete branches after merge.
- Use meaningful, conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

### Pull Requests

- Every change goes through a PR.
- CI must pass before merge.
- Review the diff before merging.
- Keep PRs focused and small.
- Document breaking/API changes.

### Main

- `main` must always remain stable.
- No direct pushes.
- Require PR + CI checks.

### Testing

- Add tests for new behavior.
- Never bypass failing tests just to merge.
- Do not make real external AI-provider calls in CI.

### Security

- Never commit secrets.
- Never log API keys, tokens, raw audio, or sensitive transcripts.
- Provider API keys stay strictly on the backend.

### Architecture

- Respect existing architecture and layer boundaries.
- Domain must remain platform/framework independent.
- External providers stay behind abstractions.
- Avoid premature infrastructure/architecture complexity.

### API

- Backend and client API contracts must stay synchronized.
- API changes require corresponding client/test/documentation updates.

### Dependencies

- Add dependencies only when justified.
- Prefer existing project capabilities.
- Upgrade dependencies deliberately.

### Documentation

- Update documentation when architecture or developer workflow changes.

### Release

- Only release tested code from `main`.
- Use version tags for releases (`v*`).

---

## Rule 1 — Never Invent Sarvam APIs

If uncertain about any of the following, consult the **latest official Sarvam documentation** at [docs.sarvam.ai](https://docs.sarvam.ai) before proceeding:

- Endpoint URLs
- Model names or versions
- Request/response parameters
- SDK method signatures
- Supported languages or language codes
- Pricing or rate limits
- Streaming/WebSocket behavior

Do not guess. Do not assume. Do not copy from outdated sources.

**Why:** Sarvam's API surface evolves. Incorrect assumptions lead to runtime failures that are difficult to diagnose.

---

## Rule 2 — Never Expose Provider Details to the Domain Layer

The domain layer (`src/app/domain/`) and application layer (`src/app/application/`) must never:

- Import the `sarvamai` SDK directly
- Reference Sarvam-specific model names, endpoints, or error codes
- Contain provider-specific response structures

All provider interaction must go through the infrastructure layer via defined protocols (`SpeechProvider`, `TranslationProvider`).

**Why:** Provider independence. The system must be able to swap Sarvam for another provider without touching business logic.

---

## Rule 3 — No Dependencies Without Justification

Every dependency added to `pyproject.toml` must have a documented reason.

Before adding a dependency, answer:

1. What does it do that the standard library cannot?
2. Is it actively maintained?
3. Does it have acceptable security posture?
4. Is the transitive dependency tree reasonable?

Document the justification in the PR description or a comment in `pyproject.toml`.

**Why:** Dependency bloat increases attack surface, build times, and maintenance burden.

---

## Rule 4 — Prefer Simple Architecture for MVP

Do not introduce any of the following unless a concrete, documented requirement exists:

- Kafka or message queues
- Kubernetes orchestration
- Microservice decomposition
- Event buses or event sourcing
- Complex distributed caching
- Service mesh
- GraphQL (REST is sufficient for this product)

The MVP architecture is:

```
Modular monolith + Async FastAPI + PostgreSQL (when needed) + WebSockets (for realtime)
```

**Why:** Premature complexity kills velocity. Clean interfaces allow future decomposition without building for it now.

---

## Rule 5 — Every Architectural Decision Requires a Reason

No structural choice should be made "because it's best practice" without explaining why it's the best practice **for this specific system**.

When making a decision, document:

1. The problem being solved
2. The alternatives considered
3. Why this alternative was chosen
4. What tradeoffs were accepted

**Why:** Undocumented decisions become cargo cult. Future engineers need to understand intent to evolve the system.

---

## Rule 6 — Every External API Integration Must Have Five Components

For every external service integration (Sarvam, future providers, databases), ensure:

| Component              | Purpose                                                          |
| ---------------------- | ---------------------------------------------------------------- |
| **Protocol/Interface** | Abstract contract in `src/app/domain/` or `src/app/application/` |
| **Implementation**     | Concrete provider in `src/app/adapters/` or `src/app/drivers/`   |
| **Mock/Fake**          | Test double for unit and integration tests                       |
| **Tests**              | Unit tests using mock, integration tests using real provider     |
| **Error Mapping**      | Provider errors mapped to domain error codes                     |

**Why:** Untested integrations fail silently. Unmocked integrations make tests slow and flaky.

---

## Rule 7 — Never Store Secrets in Source Code

Secrets must never appear in:

- Python source files
- Configuration files committed to Git
- Comments or docstrings
- Test files (use environment variables or test fixtures)
- CI/CD pipeline definitions (use secret stores)

Use environment variables loaded via `src/app/core/config.py` with Pydantic Settings.

Provide `.env.example` with placeholder values. Never commit `.env`.

**Why:** Leaked secrets are a critical security vulnerability. Recovery is expensive and damages trust.

---

## Rule 8 — Do Not Store Raw Audio by Default

Audio data (user speech) must not be persisted to disk, database, or object storage unless:

1. There is an explicit, documented product requirement
2. User consent has been obtained
3. A retention and deletion policy is in place
4. The storage is encrypted at rest

Audio should be treated as transient: received, processed, and discarded.

**Why:** Audio contains biometric and potentially sensitive personal data. Storage creates legal and ethical obligations.

---

## Rule 9 — Backend Must Be Platform-Independent

The backend must never:

- Import Android, iOS, or desktop-specific libraries
- Contain platform-detection logic
- Return platform-specific response formats
- Assume a specific client implementation

The API contract must work identically for:

- Android (Kotlin/KMP)
- iOS (Swift/KMP)
- Desktop (JVM/KMP)
- Web (if ever added)
- CLI tools
- Integration tests

**Why:** The backend serves all platforms equally. Platform coupling creates maintenance nightmares.

---

## Rule 10 — Maintain Backward-Compatible API Contracts

Once an API version is published (e.g., `/v1/`):

- Do not remove fields from response objects
- Do not change field types
- Do not change error code semantics
- Do not change URL paths
- New fields should be additive (optional)

Breaking changes require a new API version (`/v2/`).

**Why:** KMP clients are deployed on user devices and cannot be force-updated instantly. Breaking the API breaks all deployed clients.

---

## Rule 11 — External Clients Never Call Sarvam Directly

External clients must never:

- Call Sarvam AI endpoints directly
- Embed Sarvam API keys or credentials
- Reference Sarvam-specific model names or schemas

All speech recognition and translation requests must route strictly through the Effortless FastAPI backend.

**Why:** Security and architecture isolation. Exposing provider credentials in deployed client binaries is a critical security vulnerability.

---

## Rule 12 — Contract Changes Require Coordinated Updates

Never change backend API contracts or client DTOs in isolation. If an API contract changes:

1. Update `docs/contracts/api-contract.md` first.
2. Update route handlers and schemas (`src/app/api/` and `src/app/schemas/`).
3. Update any external client contract consumers.
4. Update backend tests under `src/tests/`.

**Why:** The backend and client are parts of the same product. Unilateral contract edits cause instant runtime desynchronization.

---

## Additional Guidelines

### Logging

- Use structured logging (JSON format in production)
- Include `request_id`, `user_id`, `session_id` in all log entries
- Never log API keys, auth tokens, raw audio, or user speech transcripts at INFO level or above
- Transcripts may be logged at DEBUG level in development only

### Testing

- Unit tests must not make real network calls
- Integration tests with Sarvam must be marked and skippable via environment variable
- All domain models must have dedicated unit tests
- Provider protocol compliance must be verified with contract tests

### Code Style

- Follow PEP 8
- Use type hints everywhere
- Use `async`/`await` for all I/O operations
- Prefer `Protocol` over `ABC` for interface definitions
- Use Pydantic models for all API schemas

### Git

- Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- No force pushes to main
- All changes via pull request
- `.env` in `.gitignore`
