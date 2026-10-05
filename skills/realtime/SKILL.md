---
name: realtime
description: WebSocket realtime speech-to-translation streaming pipeline architecture
---

# Purpose
Governs the architecture for low-latency voice streaming from client to backend.

# Scope
WebSocket connections, audio chunking, bidirectional message framing, and state synchronization.

# When to use
Use when implementing or maintaining the live microphone-to-translated-text streaming feature.

# Architecture rules
- Voice streaming utilizes WebSocket over TLS (WSS) to the FastAPI `/api/v1/realtime/translate` endpoint.
- Client audio must be captured and framed in small PCM buffers (100ms-200ms at 16kHz mono).
- The client UI displays partial speech transcripts immediately, but translates only stabilized/final segments to avoid excessive translation overhead and jitter.

# Preferred patterns
- Reactive streams using Kotlin `Flow<AudioChunk>` and WebSocket channels.
- Connection state machines: `Disconnected` → `Connecting` → `Streaming` → `Reconnecting`.
- Decouple audio recording hardware from network transmission logic.

# Anti-patterns
- ❌ Buffering minutes of audio before sending.
- ❌ Translating every 100ms partial word change (causes jitter and cost explosion).
- ❌ Persisting raw audio on disk or unencrypted storage.

# Testing requirements
- Test WebSocket message serialization and frame handlers with fake sockets.

# Platform considerations
- Android requires `RECORD_AUDIO` permission.
- iOS requires `NSMicrophoneUsageDescription` in Info.plist.

# Related documentation
- [docs/contracts/api-contract.md](../../docs/contracts/api-contract.md)
