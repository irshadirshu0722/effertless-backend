---
name: performance
description: Client and backend performance guidelines, memory limits, and latency targets
---

# Purpose
Governs performance standards, latency budgets, and memory management for Effortless.

# Scope
UI recomposition, audio buffer allocation, network latency, and memory footprints.

# When to use
Use when processing audio streams, updating high-frequency UI components, or evaluating system responsiveness.

# Architecture rules
- **Latency Budget**: Total end-to-end voice-to-translated-text target is < 1500ms for short utterances.
- Never allocate large objects inside high-frequency audio processing loops.
- Audio recording and socket streaming must run off the main UI thread.

# Preferred patterns
- Reuse byte buffers where appropriate for PCM streaming.
- Use `derivedStateOf` and stable types in Compose to prevent unnecessary recompositions.
- Measure latency explicitly using timestamp deltas in domain entities.

# Anti-patterns
- ❌ Heavy JSON parsing or transformation on the main UI thread.
- ❌ Leaking coroutine jobs or memory in long-running streaming sessions.
- ❌ Polling when push-based WebSocket streams are available.

# Testing requirements
- Benchmark and profile memory allocation during audio streaming phases.

# Platform considerations
- iOS keyboard extensions are hard-limited by the OS to ~30MB memory. Keep allocations minimal.

# Related documentation
- [skills/realtime/SKILL.md](../realtime/SKILL.md)
