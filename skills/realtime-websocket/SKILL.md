---
name: realtime-websocket
description: Guidelines for realtime speech-to-translation WebSocket implementation
---

# Realtime WebSocket Skill

## Purpose

Ensure correct implementation of the realtime WebSocket pipeline for streaming speech-to-translation.

## When to Use

- Implementing the WebSocket endpoint
- Managing session lifecycle
- Integrating with Sarvam Realtime API
- Designing the translation timing strategy

## Architectural Principles

1. **Translate only finals**: Never translate partial transcripts
2. **State machine**: Session follows IDLE → CONNECTING → LISTENING → TRANSCRIBING → TRANSLATING → COMPLETED
3. **Binary audio, JSON events**: Audio chunks as binary frames; all events as JSON text frames
4. **Auth before accept**: Validate authentication before accepting the WebSocket

## Rules

- Max session duration: 5 minutes
- Max audio frame size: 64 KB
- Idle timeout: 30 seconds (no audio received)
- Always generate a unique `session_id` per connection
- Close Sarvam upstream WS when client disconnects
- Send `error` events for recoverable errors (don't close WS)
- Use close codes: 4001 (auth), 4002 (invalid lang), 4003 (timeout), 4010 (internal)

## Anti-patterns

- ❌ Translating every partial transcript (wasteful, poor quality)
- ❌ Accepting WebSocket before validating auth
- ❌ Leaving upstream Sarvam connection open after client disconnect
- ❌ Blocking on translation before processing more audio
- ❌ Sending binary data in text frames or vice versa

## Implementation Guidelines

```python
@router.websocket("/v1/realtime/translate")
async def realtime(ws: WebSocket):
    # 1. Auth
    if not validate(ws.query_params.get("api_key")):
        await ws.close(code=4001)
        return

    # 2. Accept + create session
    await ws.accept()
    session = RealtimeSession(...)

    # 3. Dual loop: receive audio + receive Sarvam events
    # Use asyncio.gather or task groups

    # 4. Cleanup on disconnect
```

## Testing Requirements

- Test connection lifecycle (connect → stream → end)
- Test auth rejection (invalid key → close 4001)
- Test idle timeout (no audio → close 4003)
- Test client disconnect cleanup
- Test error recovery (Sarvam error → error event, session continues)

## Relevant Project Documentation

- [docs/architecture/realtime-pipeline.md](../../docs/architecture/realtime-pipeline.md)
- [docs/api/realtime.md](../../docs/api/realtime.md)
