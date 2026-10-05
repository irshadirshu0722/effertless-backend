# AI Evaluation Framework

## Problem

Typeless relies on AI models for speech recognition and translation. Traditional unit tests with exact string matching are insufficient — two translations can be semantically equivalent without being identical strings.

## Requirements

1. Evaluate speech recognition accuracy (Word Error Rate)
2. Evaluate translation quality (semantic correctness, fluency, adequacy)
3. Support regression testing when models are updated
4. Benchmark different model/provider configurations
5. Automate evaluation where possible

## Evaluation Dimensions

### Speech Recognition

| Metric | Description | Measurement |
|---|---|---|
| **Word Error Rate (WER)** | (Substitutions + Deletions + Insertions) / Reference Words | Lower is better; < 10% is good |
| **Language ID Accuracy** | Correct language detection rate | Percentage correct across test set |
| **Code-mix Accuracy** | Accuracy on Hindi-English mixed speech | WER on code-mixed subset |
| **Punctuation Accuracy** | Correct sentence boundary detection | F1 score on punctuation marks |

### Translation

| Metric | Description | Measurement |
|---|---|---|
| **Semantic Correctness** | Does the translation convey the same meaning? | Human evaluation (1–5 scale) |
| **Adequacy** | Is all information from the source preserved? | Human evaluation (1–5 scale) |
| **Fluency** | Does the translation read naturally in the target language? | Human evaluation (1–5 scale) |
| **Terminology** | Are domain-specific terms translated correctly? | Exact match on key terms |
| **Code-mix Handling** | Are English words in Hindi input handled correctly? | Manual review |

## Test Dataset Structure

```
evaluation/
├── speech/
│   ├── dataset.json           # Test cases with reference transcripts
│   └── audio/                 # Test audio files
│       ├── hi_IN_001.wav
│       ├── hi_IN_002.wav
│       └── ...
│
└── translation/
    ├── dataset.json           # Test cases with reference translations
    └── reports/               # Evaluation results
```

### Speech Dataset Format

```json
{
  "test_cases": [
    {
      "id": "stt_hi_001",
      "audio_file": "audio/hi_IN_001.wav",
      "language": "hi-IN",
      "reference_transcript": "मुझे कल ऑफिस जाना है",
      "tags": ["clean", "formal"],
      "notes": "Clear speech, standard Hindi"
    },
    {
      "id": "stt_hi_002",
      "audio_file": "audio/hi_IN_002.wav",
      "language": "hi-IN",
      "reference_transcript": "मुझे tomorrow office जाना है",
      "tags": ["code-mixed", "hinglish"],
      "notes": "Hindi-English code-mixed speech"
    }
  ]
}
```

### Translation Dataset Format

```json
{
  "test_cases": [
    {
      "id": "tr_hi_en_001",
      "source_text": "मुझे कल ऑफिस जाना है",
      "source_language": "hi-IN",
      "target_language": "en-IN",
      "reference_translations": [
        "I have to go to the office tomorrow.",
        "I need to go to office tomorrow.",
        "I have to go to the office tomorrow"
      ],
      "semantic_meaning": "Speaker needs to visit their workplace the next day",
      "tags": ["everyday", "formal"]
    }
  ]
}
```

> **Note**: Multiple reference translations are provided because there is no single "correct" translation.

## Automated Evaluation

### BLEU Score (Baseline)

BLEU provides a rough automated translation quality score. Not perfect, but useful for regression detection:

```python
from nltk.translate.bleu_score import sentence_bleu

def evaluate_translation_bleu(hypothesis: str, references: list[str]) -> float:
    """Calculate BLEU score against multiple reference translations."""
    ref_tokens = [ref.split() for ref in references]
    hyp_tokens = hypothesis.split()
    return sentence_bleu(ref_tokens, hyp_tokens)
```

### Semantic Similarity (Better)

Use embedding-based similarity for more meaningful comparison:

```python
# Future: use Sarvam embeddings or sentence-transformers
def evaluate_semantic_similarity(hypothesis: str, reference: str) -> float:
    """Calculate cosine similarity between embeddings."""
    ...
```

## Evaluation Workflow

```
1. Collect/update test dataset
2. Run pipeline against test dataset
3. Calculate metrics (WER, BLEU, semantic similarity)
4. Compare against baseline scores
5. Flag regressions
6. Generate evaluation report
```

### When to Run

| Trigger | Scope |
|---|---|
| Model version change | Full evaluation suite |
| Provider configuration change | Affected language pairs |
| Monthly schedule | Full regression check |
| New language pair added | New pair + related pairs |

## Language-Pair Coverage

Priority evaluation pairs (most common expected usage):

| Pair | Priority | Why |
|---|---|---|
| Hindi → English | P0 | Most common use case |
| English → Hindi | P0 | Reverse direction |
| Tamil → English | P1 | Major Dravidian language |
| Malayalam → English | P1 | Major Dravidian language |
| Hindi → Malayalam (pivot) | P1 | Tests pivot quality |
| Bengali → English | P2 | Large speaker population |
| Telugu → English | P2 | Large speaker population |

## Future Evolution

1. **LLM-as-judge**: Use Sarvam-105B to evaluate translation quality
2. **Continuous evaluation**: Run on production traffic sample (with consent)
3. **A/B testing framework**: Compare model versions on live traffic
4. **User feedback loop**: Collect user corrections to improve evaluation dataset
