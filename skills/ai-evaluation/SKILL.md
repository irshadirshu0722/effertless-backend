---
name: ai-evaluation
description: Guidelines for evaluating AI model quality (speech and translation)
---

# AI Evaluation Skill

## Purpose

Ensure systematic evaluation of speech recognition and translation quality, preventing silent regressions when models or configurations change.

## When to Use

- Updating Sarvam model versions
- Adding support for new languages
- Comparing translation quality across models
- Investigating user-reported quality issues

## Architectural Principles

1. **No exact string matching**: Translations can be semantically equivalent without being identical
2. **Multiple references**: Each test case has multiple acceptable translations
3. **Per-language evaluation**: Quality varies by language; evaluate each independently
4. **Automated + human**: BLEU/WER for automated regression; human review for quality decisions

## Rules

- Evaluation dataset lives in `evaluation/` directory
- Every model upgrade requires running the full evaluation suite
- WER > 15% on a priority language is a blocker
- BLEU score regression > 5% on priority pairs requires investigation
- New languages must have at least 20 test cases before launch

## Anti-patterns

- ❌ Using exact string equality for translation tests: `assert result == "expected"`
- ❌ Evaluating only Hindi→English and assuming other pairs are fine
- ❌ Shipping a model upgrade without evaluation
- ❌ Relying solely on automated metrics (human review is essential)

## Relevant Project Documentation

- [docs/ai/evaluation.md](../../docs/ai/evaluation.md)
- [docs/ai/sarvam-model-strategy.md](../../docs/ai/sarvam-model-strategy.md)
