---
name: translation
description: Guidelines for the text translation pipeline (Mayura and Sarvam-Translate)
---

# Translation Skill

## Purpose

Ensure correct implementation of text translation using Sarvam translation models with proper model selection routing.

## When to Use

- Implementing or modifying translation features
- Adding new language pair support
- Configuring the TranslationRouter
- Debugging translation quality

## Architectural Principles

1. **Router-based selection**: TranslationRouter selects Mayura or Sarvam-Translate based on language pair
2. **Mayura for quality**: Default for its 10 supported languages (colloquial/code-mixed)
3. **Sarvam-Translate for coverage**: Fallback for all 22 languages (formal)
4. **Pivot for Indic-Indic**: Use English as intermediate for Indic→Indic pairs

## Rules

- Mayura: max 1,000 characters; Sarvam-Translate: max 2,000 characters
- Validate language pair before calling any translation API
- Use `modern-colloquial` style for Mayura (conversational keyboard input)
- Log translation latency and model used (without logging content)
- Return domain `TranslationResult`, never raw Sarvam response

## Anti-patterns

- ❌ Always using Sarvam-Translate and ignoring Mayura's quality advantage
- ❌ Translating partial realtime transcripts
- ❌ Hardcoding the translation model instead of using config
- ❌ Letting clients discover unsupported pairs via Sarvam errors

## Implementation Guidelines

```python
# TranslationRouter decision tree
1. Config override? → Use forced model
2. Both languages in Mayura set + colloquial style? → mayura:v1
3. Otherwise → sarvam-translate:v1

# Indic-to-Indic pivot
1. Hindi → Malayalam: Hindi →(Mayura)→ English →(Mayura)→ Malayalam
2. Assamese → Hindi: Assamese →(Sarvam-Translate)→ English →(Mayura)→ Hindi
```

## Testing Requirements

- Test all 10 Mayura language pairs (bidirectional = 20 combinations)
- Test at least 3 Sarvam-Translate-only languages
- Test at least 2 Indic-to-Indic pivot translations
- Test unsupported language pair rejection
- Test text length validation

## Relevant Project Documentation

- [docs/ai/sarvam-model-strategy.md](../../docs/ai/sarvam-model-strategy.md)
- [docs/architecture/ai-pipeline.md](../../docs/architecture/ai-pipeline.md)
- [docs/architecture/language-system.md](../../docs/architecture/language-system.md)
- [docs/api/translation.md](../../docs/api/translation.md)
