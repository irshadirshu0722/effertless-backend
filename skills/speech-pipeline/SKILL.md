---
name: speech-pipeline
description: Guidelines for the speech recognition pipeline (Saaras STT integration)
---

# Speech Pipeline Skill

## Purpose

Ensure correct implementation of the speech-to-text pipeline using Sarvam Saaras.

## When to Use

- Implementing or modifying speech recognition features
- Handling audio input validation
- Choosing between REST and Realtime STT APIs
- Debugging transcription issues

## Architectural Principles

1. **Audio is transient**: Never persist audio data unless explicitly required
2. **Validate before sending**: Check format, size, and duration before calling Saaras
3. **Mode selection**: Use `transcribe` by default; `translate` only as an optimization
4. **Language detection**: Support `auto` mode but prefer explicit language when available

## Rules

- REST API: max 30 seconds audio, max 5 MB file size
- Realtime API: use `saaras:v4-realtime` model
- Supported formats: WAV, MP3, AAC, FLAC, OGG, OPUS, WebM
- Always log speech latency (without logging the transcript content)
- Return domain `Transcript` object, never raw Sarvam response

## Anti-patterns

- ❌ Storing raw audio in database or filesystem
- ❌ Logging transcript content at INFO level
- ❌ Using the deprecated `/speech-to-text-translate` endpoint
- ❌ Assuming all languages have equal recognition quality

## Testing Requirements

- Unit tests with `FakeSpeechProvider` (deterministic transcript)
- Test with empty audio, corrupt audio, unsupported format
- Integration tests with real audio files for priority languages (Hindi, Tamil, Malayalam)

## Relevant Project Documentation

- [docs/ai/sarvam-model-strategy.md](../../docs/ai/sarvam-model-strategy.md)
- [docs/architecture/ai-pipeline.md](../../docs/architecture/ai-pipeline.md)
- [docs/api/speech.md](../../docs/api/speech.md)
