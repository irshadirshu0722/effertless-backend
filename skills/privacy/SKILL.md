---
name: privacy
description: Privacy guidelines for handling audio and transcript data
---

# Privacy Skill

## Purpose

Ensure responsible handling of voice data, transcripts, and translations in the Typeless backend.

## When to Use

- Implementing any feature that processes audio or text
- Adding logging statements
- Designing data persistence
- Reviewing third-party data flows

## Architectural Principles

1. **Ephemeral by default**: Audio, transcripts, and translations are not persisted
2. **Content-free logging**: Never log speech content at INFO or above
3. **Metadata only**: Usage tracking records only metadata (language, latency, status)
4. **Consent-aware**: Users must know audio is sent to third-party AI services

## Rules

- Never persist raw audio unless explicitly consented and documented
- Never log transcript or translation text at INFO/WARNING/ERROR levels
- DEBUG-level content logging allowed only in development
- Usage tracking: timestamp, language pair, latency, model, status — NOT content
- Document all data flows to third parties (Sarvam)

## Anti-patterns

- ❌ `logger.info(f"Translated: {transcript} → {translation}")`
- ❌ Storing audio files "just in case"
- ❌ Logging user speech for debugging in production
- ❌ Assuming Sarvam's data policy without reviewing it

## Relevant Project Documentation

- [docs/architecture/privacy.md](../../docs/architecture/privacy.md)
