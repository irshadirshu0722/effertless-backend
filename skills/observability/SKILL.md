---
name: observability
description: Logging, metrics, and monitoring guidelines for the Typeless backend
---

# Observability Skill

## Purpose

Ensure comprehensive, privacy-safe observability across all Typeless backend operations.

## When to Use

- Adding logging to new features
- Tracking latency for AI operations
- Setting up health checks
- Designing error monitoring

## Architectural Principles

1. **Structured logging**: JSON format, consistent fields
2. **Request correlation**: Every log entry includes `request_id`
3. **Latency at every stage**: Speech, translation, total — all measured
4. **Privacy-safe**: No content in logs at INFO or above
5. **Primary metric**: Speech-stop to text-appear latency

## Rules

- Use `structlog` for all logging
- Every log entry: `request_id`, `user_id` (if available), `status`
- AI operations: include `model`, `provider`, `source_language`, `target_language`, `latency_ms`
- Never log: API keys, transcripts, translations, audio data
- Health check at `GET /health` — always available

## Anti-patterns

- ❌ Using `print()` for debugging (use `logger.debug()`)
- ❌ Logging content: `logger.info(f"Result: {translation}")`
- ❌ Missing latency tracking on AI operations
- ❌ Inconsistent log field names

## Relevant Project Documentation

- [docs/architecture/observability.md](../../docs/architecture/observability.md)
