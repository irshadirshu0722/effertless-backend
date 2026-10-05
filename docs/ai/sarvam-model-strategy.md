# Sarvam Model Strategy

> **Last verified**: September 2026 against [docs.sarvam.ai](https://docs.sarvam.ai)
>
> **Important**: Always verify model names, parameters, and capabilities against the latest Sarvam documentation before making implementation changes. See `AGENTS.md` Rule 1.

## Speech Recognition — Saaras

### Model Selection

| Model | Use Case | Recommendation |
|---|---|---|
| `saaras:v4` | **Primary — REST API** | Latest model with Global English support. Use for all new integrations. |
| `saaras:v3` | Fallback — REST API | Previous generation. Only if v4 regression detected. |
| `saaras:v4-realtime` | **Primary — Realtime WebSocket** | Latest model for streaming. Supports partial transcripts and VAD. |
| `saaras:v3-realtime` | Fallback — Realtime WebSocket | Previous generation realtime model. |

**Decision**: Use `saaras:v4` (REST) and `saaras:v4-realtime` (WebSocket) as primary models. They offer the best accuracy and broadest language support.

### Supported Languages

Saaras supports all 22 scheduled Indian languages plus English (23 total). It also supports automatic language detection (`language_code="auto"`).

### Output Modes

| Mode | Output | Use in Typeless |
|---|---|---|
| `transcribe` | Text in original language | **Primary** — standard speech-to-text |
| `translate` | English translation | **Optimization** — skip translation step for X→English pairs |
| `verbatim` | Exact with disfluencies | Not for keyboard input (too noisy) |
| `translit` | Romanized text | Future feature (transliteration keyboard mode) |
| `codemix` | Preserves code-mixing | Future feature (Hinglish input mode) |

### Key Capabilities

- **Language Identification**: Automatic detection across 22+ languages
- **Code-mixed speech**: Handles Hindi-English mixing (Hinglish), etc.
- **Noisy audio**: Optimized for real-world conditions
- **Keyterms**: Up to 50 terms for domain-specific accuracy (v4 only)
- **Punctuation**: Automatic punctuation in transcripts

### Constraints

| Constraint | REST API | Batch API | Realtime WS |
|---|---|---|---|
| **Max duration** | 30 seconds | 2 hours | Session-based |
| **Audio formats** | WAV, MP3, AAC, FLAC, OGG, OPUS, AIFF, MP4/M4A, AMR, WMA, WebM | Same | PCM/WAV recommended |
| **Partial transcripts** | ❌ | ❌ | ✅ |
| **VAD tuning** | ❌ | ❌ | ✅ (millisecond-level) |
| **Mid-stream reconfig** | ❌ | ❌ | ✅ |

### API Usage

```python
# REST API
from sarvamai import AsyncSarvamAI

client = AsyncSarvamAI(api_subscription_key="...")

response = await client.speech_to_text.transcribe(
    file=open("audio.wav", "rb"),
    model="saaras:v4",
    language_code="hi-IN",  # or "auto"
    mode="transcribe",
)
print(response.transcript)

# Realtime WebSocket
# Endpoint: wss://api.sarvam.ai/speech-to-text-realtime/ws
# Auth: API-SUBSCRIPTION-KEY header or subprotocol
# Model: saaras:v4-realtime
```

---

## Translation — Mayura

### Model

`mayura:v1` — Optimized for colloquial, conversational, and code-mixed translation.

### When to Use

- **Default for supported languages** — Best quality for conversational keyboard input
- Hindi ↔ English, Tamil ↔ English, etc. (10 Indic languages + English)
- Code-mixed input (Hinglish → English, Tanglish → English)
- Informal/colloquial text

### Supported Languages (10 + English)

Bengali (bn-IN), Gujarati (gu-IN), Hindi (hi-IN), Kannada (kn-IN), Malayalam (ml-IN), Marathi (mr-IN), Odia (od-IN), Punjabi (pa-IN), Tamil (ta-IN), Telugu (te-IN), English (en-IN)

### Translation Styles

| Style | Use Case |
|---|---|
| `formal` | Professional communication |
| `modern-colloquial` | **Default for Typeless** — natural conversational tone |
| `classic-colloquial` | Traditional informal language |
| `code-mixed` | Preserves English words in Indic output |

### Constraints

| Constraint | Value |
|---|---|
| **Input limit** | 1,000 characters per request |
| **Direction** | English ↔ Indic (bidirectional) |
| **Indic → Indic** | Not directly supported (pivot via English) |
| **Auto-detect** | `source_language_code="auto"` |
| **Script control** | Roman/native script, numeral format |

### API Usage

```python
response = await client.text.translate(
    input="मुझे कल ऑफिस जाना है",
    source_language_code="hi-IN",
    target_language_code="en-IN",
    model="mayura:v1",
)
print(response.translated_text)
```

---

## Translation — Sarvam-Translate

### Model

`sarvam-translate:v1` — Broad coverage across all 22 scheduled Indian languages.

### When to Use

- Languages NOT supported by Mayura (Assamese, Bodo, Dogri, Kashmiri, Konkani, Maithili, Manipuri, Nepali, Sanskrit, Santali, Sindhi, Urdu)
- Formal/structured text translation
- When explicitly configured to override Mayura

### Supported Languages (22 + English)

All 22 scheduled Indian languages: Assamese (as-IN), Bengali (bn-IN), Bodo (brx-IN), Dogri (doi-IN), Gujarati (gu-IN), Hindi (hi-IN), Kannada (kn-IN), Kashmiri (ks-IN), Konkani (kok-IN), Maithili (mai-IN), Malayalam (ml-IN), Manipuri (mni-IN), Marathi (mr-IN), Nepali (ne-IN), Odia (od-IN), Punjabi (pa-IN), Sanskrit (sa-IN), Santali (sat-IN), Sindhi (sd-IN), Tamil (ta-IN), Telugu (te-IN), Urdu (ur-IN), plus English (en-IN).

### Constraints

| Constraint | Value |
|---|---|
| **Input limit** | 2,000 characters per request |
| **Direction** | English ↔ Indic (bidirectional) |
| **Indic → Indic** | Not directly supported (pivot via English) |
| **Auto-detect** | `source_language_code="auto"` |
| **Style** | Formal/structured (not colloquial) |

### API Usage

```python
response = await client.text.translate(
    input="Hello, how are you?",
    source_language_code="en-IN",
    target_language_code="as-IN",  # Assamese (not supported by Mayura)
    model="sarvam-translate:v1",
)
```

---

## Translation Router — Model Selection Logic

```python
def select_translation_model(source: str, target: str, style: str = "colloquial") -> str:
    """Select the best translation model for a given language pair and style.

    Decision tree:
    1. If force_model is configured → use that model
    2. If both languages are in Mayura's 11-language set AND style is not formal → Mayura
    3. Otherwise → Sarvam-Translate

    Returns:
        Model identifier string (e.g., "mayura:v1" or "sarvam-translate:v1")
    """
    MAYURA_LANGUAGES = {
        "en-IN", "hi-IN", "bn-IN", "gu-IN", "kn-IN",
        "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN"
    }

    if source in MAYURA_LANGUAGES and target in MAYURA_LANGUAGES and style != "formal":
        return "mayura:v1"

    return "sarvam-translate:v1"
```

---

## Sarvam-105B (LLM)

**Not used in the initial speech→translation pipeline.**

`sarvam-105b` is a large language model suitable for:
- Text rewriting and tone adjustment
- Grammar correction
- Contextual rewriting
- Conversational AI responses
- AI keyboard suggestions
- Text expansion and intelligent editing

See [docs/ai/future-llm-layer.md](future-llm-layer.md) for the planned integration architecture.

---

## Pricing Summary

| Service | Rate (INR) |
|---|---|
| **STT (Saaras)** | ₹30/hour of audio (base) |
| **STT with translation mode** | ₹45/hour of audio |
| **Translation (Mayura/Sarvam-Translate)** | Consult latest docs |

> **Note**: Free credits (₹100) available for new accounts. Billing is per-second for STT.

---

## Model Lifecycle

| Event | Action Required |
|---|---|
| New Saaras version released | Evaluate accuracy; update `SARVAM_SPEECH_MODEL` config |
| New translation model released | Evaluate quality; update router logic |
| Model deprecated | Migrate before deprecation deadline |
| Language support expanded | Update LanguageRegistry; expand capability flags |
| API endpoint changed | Update infrastructure layer; check SDK version |

All model version changes should be gated behind configuration and validated with the AI evaluation framework before production rollout.
