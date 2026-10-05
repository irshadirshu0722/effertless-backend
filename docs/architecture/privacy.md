# Privacy Architecture

## Problem

Typeless processes voice recordings and produces text transcripts — both of which contain potentially sensitive personal data. The system must handle this data responsibly, minimizing storage and exposure.

## Requirements

1. Audio is transient by default — not persisted
2. Transcripts are not persisted unless explicitly required
3. Logging does not capture speech content
4. Third-party data processing is documented
5. Data retention and deletion policies are defined
6. Compliance with user consent expectations

## Architecture

### Data Flow and Retention

| Data Type | Enters Backend | Persisted | Retention | Purpose |
|---|---|---|---|---|
| Raw audio | Yes (HTTP/WS) | ❌ No | Discarded after processing | Speech recognition input |
| Source transcript | Yes (from Sarvam) | ❌ No (MVP) | Discarded after response | Translation input |
| Translated text | Yes (from Sarvam) | ❌ No (MVP) | Discarded after response | Client response |
| User ID | Yes (auth) | ✅ Yes | Account lifetime | Authentication, rate limiting |
| Usage metadata | Yes (generated) | ✅ Yes (future) | 90 days | Analytics, billing, abuse prevention |
| Language preference | Yes (from client) | ✅ Yes (future) | Account lifetime | User experience |

### No-Persist-by-Default Policy

The MVP operates in **ephemeral mode**:

```
Client sends audio
    → Backend processes through Sarvam
    → Backend returns result to client
    → Audio, transcript, and translation are garbage collected
    → No record of the content exists on the backend
```

**When persistence is introduced** (for usage tracking, analytics):

- Only metadata is persisted (language pair, timestamp, latency, success/failure)
- Content (transcript, translation) is NOT persisted
- Audio is NEVER persisted unless an explicit, consented feature requires it

### Third-Party Data Processing

| Provider | Data Sent | Data Returned | Provider Retention |
|---|---|---|---|
| Sarvam AI (STT) | Audio bytes | Transcript text | Consult Sarvam's data policy |
| Sarvam AI (Translation) | Source text | Translated text | Consult Sarvam's data policy |

> **Action Item**: Before production launch, review Sarvam AI's data processing agreement (DPA) and privacy policy to understand:
> - Whether Sarvam retains audio/text for model training
> - Data residency (where processing occurs)
> - Options for opting out of data retention

### Logging Policy

| Log Level | What's Logged | What's NOT Logged |
|---|---|---|
| **ERROR** | Error codes, request IDs, provider name | Transcript content, audio data |
| **WARNING** | Rate limit events, validation failures | User speech, translations |
| **INFO** | Request metadata (language pair, latency, status) | Any content data |
| **DEBUG** (dev only) | May include truncated transcript (first 50 chars) | Full audio, full transcripts, API keys |

```python
# ✅ Acceptable logging
logger.info(
    "Translation completed",
    extra={
        "request_id": request_id,
        "source_language": "hi-IN",
        "target_language": "en-IN",
        "latency_ms": 234,
        "model": "mayura:v1",
        "status": "success",
    },
)

# ❌ NEVER log this
logger.info(f"Translated: '{transcript}' → '{translation}'")
```

### Consent Model

For MVP:
- Users implicitly consent to ephemeral processing by using the application
- Terms of Service must disclose that audio is sent to a third-party AI service (Sarvam)
- No audio is stored, so data deletion requests are trivially satisfied

For production:
- Explicit consent for any persistent data collection
- Data export capability (user's usage history)
- Data deletion capability (remove all user data)

## Design Decisions

| Decision | Rationale |
|---|---|
| **Ephemeral by default** | Minimizes legal obligations and security surface |
| **Content-free logging** | Prevents accidental exposure of sensitive speech in log aggregators |
| **Metadata-only persistence** | Enables analytics without storing personal content |

## Failure Modes

| Failure | Impact | Mitigation |
|---|---|---|
| Accidental content logging | Speech data in log storage | Log audit; structured logging prevents format-string leaks |
| Sarvam retains data unexpectedly | Privacy violation | DPA review; contractual controls |
| Debug logging in production | Content leakage | Log level enforcement; CI check for debug statements |

## Future Evolution

1. **GDPR/DPDPA compliance**: Formal data processing records, consent management
2. **On-device processing**: Process speech on device to avoid sending audio to backend at all
3. **End-to-end encryption**: Encrypt audio in transit and at rest if persistence is added
4. **Anonymization**: Strip user identity from usage data for analytics
