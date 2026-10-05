# Future LLM Layer

## Overview

The initial Typeless pipeline uses dedicated speech (Saaras) and translation (Mayura/Sarvam-Translate) models. This document describes how a large language model (LLM) layer — specifically **Sarvam-105B** — could be added later without coupling to the core translation system.

## Why Not Now

The core pipeline (speech → translation) is best served by purpose-built models:
- **Saaras**: Optimized for speech recognition with language-specific acoustic models
- **Mayura**: Optimized for colloquial translation quality
- **Sarvam-Translate**: Optimized for broad language coverage

An LLM adds latency, cost, and complexity without improving the core translation task.

## When to Introduce

An LLM layer becomes valuable when the product requires:

| Feature | Description |
|---|---|
| **Tone adjustment** | "Make this more formal" / "Make this casual" |
| **Grammar correction** | Fix grammatical errors in the translated output |
| **Contextual rewriting** | Adapt translation based on conversation context |
| **Text expansion** | "Elaborate on this" from a short input |
| **Keyboard suggestions** | Predict next words or phrases |
| **Conversational AI** | Chat-style responses (e.g., smart reply) |
| **Summarization** | Condense long translations |

## Architecture

### Integration Point

The LLM layer is an **optional post-processing step** that sits after translation:

```
Audio
  ↓
Saaras (Speech)
  ↓
Transcript
  ↓
Mayura / Sarvam-Translate (Translation)
  ↓
Raw Translation
  ↓
[Optional] Sarvam-105B (Post-processing)
  ↓
Final Output
```

### Provider Protocol

```python
class TextProcessor(Protocol):
    """Protocol for optional text post-processing."""

    async def process(
        self,
        text: str,
        instruction: str,
        language: Language,
    ) -> ProcessedText:
        """Process text with an instruction (e.g., 'make formal', 'fix grammar')."""
        ...
```

### Implementation

```python
class Sarvam105BProcessor:
    """Sarvam-105B implementation for text post-processing."""

    def __init__(self, client: AsyncSarvamAI):
        self._client = client

    async def process(self, text: str, instruction: str, language: Language) -> ProcessedText:
        response = await self._client.chat.completions.create(
            model="sarvam-105b",
            messages=[
                {"role": "system", "content": self._build_system_prompt(instruction, language)},
                {"role": "user", "content": text},
            ],
        )
        return ProcessedText(
            original=text,
            processed=response.choices[0].message.content,
            instruction=instruction,
        )
```

### Key Principles

1. **Opt-in**: LLM processing is never mandatory; the client explicitly requests it
2. **Decoupled**: Core translation works without the LLM layer
3. **Versioned prompts**: System prompts are version-controlled and evaluated
4. **Latency-aware**: Client is informed of additional latency when LLM processing is requested
5. **Cost-aware**: LLM calls are metered separately from translation

## API Design (Future)

```json
// POST /v1/translation
{
  "text": "मुझे कल ऑफिस जाना है",
  "source_language": "hi-IN",
  "target_language": "en-IN",
  "post_processing": {
    "enabled": true,
    "instruction": "formal_tone"
  }
}
```

## Prompt Management

When introduced, prompts will be:
- Stored as version-controlled files (`prompts/v1/formal_tone.txt`)
- Tested with the AI evaluation framework
- A/B testable via configuration
- Monitored for hallucination and quality regression
