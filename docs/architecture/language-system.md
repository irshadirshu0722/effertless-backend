# Language System Architecture

## Problem

Typeless must manage a complex matrix of language support across multiple AI models, each with different capabilities. Language codes, display names, and capability flags must be centralized to prevent scattered hardcoding.

## Requirements

1. Single source of truth for all language metadata
2. Capability flags per model (Saaras speech, Mayura translation, Sarvam-Translate)
3. Language pair validation before calling external APIs
4. Power the `GET /v1/languages` endpoint and KMP UI
5. BCP-47 language codes (e.g., `hi-IN`) consistent with Sarvam API

## Architecture

### Language Model

```python
@dataclass(frozen=True)
class Language:
    """Represents a supported language with its metadata and capabilities."""

    code: str              # BCP-47 code, e.g., "hi-IN"
    name: str              # English display name, e.g., "Hindi"
    native_name: str       # Native script name, e.g., "हिन्दी"
    saaras_speech: bool    # Supported by Saaras STT
    mayura_translation: bool  # Supported by Mayura translation
    sarvam_translation: bool  # Supported by Sarvam-Translate


@dataclass(frozen=True)
class LanguagePair:
    """A validated source-target language pair."""

    source: Language
    target: Language

    def __post_init__(self):
        if self.source.code == self.target.code:
            raise ValueError("Source and target language must differ")
```

### Language Registry

```python
class LanguageRegistry:
    """Centralized registry of supported languages and their capabilities."""

    def __init__(self):
        self._languages: dict[str, Language] = {}
        self._load_languages()

    def get(self, code: str) -> Language:
        """Get language by BCP-47 code. Raises InvalidLanguageError if not found."""
        ...

    def list_all(self) -> list[Language]:
        """List all registered languages."""
        ...

    def list_speech_supported(self) -> list[Language]:
        """Languages supported for speech recognition."""
        ...

    def list_translation_supported(self) -> list[Language]:
        """Languages supported for translation (any model)."""
        ...

    def validate_pair(self, source_code: str, target_code: str) -> LanguagePair:
        """Validate and return a LanguagePair. Raises appropriate errors."""
        source = self.get(source_code)
        target = self.get(target_code)

        if not self._is_translation_supported(source, target):
            raise UnsupportedLanguagePairError(source_code, target_code)

        return LanguagePair(source=source, target=target)

    def can_translate_direct(self, source: Language, target: Language) -> bool:
        """Check if direct translation is possible (without English pivot)."""
        english_codes = {"en-IN"}
        return source.code in english_codes or target.code in english_codes

    def requires_pivot(self, source: Language, target: Language) -> bool:
        """Check if translation requires English pivot."""
        return not self.can_translate_direct(source, target)
```

### Complete Language Table

| Code | Name | Native Name | Saaras STT | Mayura | Sarvam-Translate |
|---|---|---|---|---|---|
| `en-IN` | English | English | ✅ | ✅ | ✅ |
| `hi-IN` | Hindi | हिन्दी | ✅ | ✅ | ✅ |
| `bn-IN` | Bengali | বাংলা | ✅ | ✅ | ✅ |
| `gu-IN` | Gujarati | ગુજરાતી | ✅ | ✅ | ✅ |
| `kn-IN` | Kannada | ಕನ್ನಡ | ✅ | ✅ | ✅ |
| `ml-IN` | Malayalam | മലയാളം | ✅ | ✅ | ✅ |
| `mr-IN` | Marathi | मराठी | ✅ | ✅ | ✅ |
| `od-IN` | Odia | ଓଡ଼ିଆ | ✅ | ✅ | ✅ |
| `pa-IN` | Punjabi | ਪੰਜਾਬੀ | ✅ | ✅ | ✅ |
| `ta-IN` | Tamil | தமிழ் | ✅ | ✅ | ✅ |
| `te-IN` | Telugu | తెలుగు | ✅ | ✅ | ✅ |
| `as-IN` | Assamese | অসমীয়া | ✅ | ❌ | ✅ |
| `brx-IN` | Bodo | बड़ो | ✅ | ❌ | ✅ |
| `doi-IN` | Dogri | डोगरी | ✅ | ❌ | ✅ |
| `ks-IN` | Kashmiri | كٲشُر | ✅ | ❌ | ✅ |
| `kok-IN` | Konkani | कोंकणी | ✅ | ❌ | ✅ |
| `mai-IN` | Maithili | मैथिली | ✅ | ❌ | ✅ |
| `mni-IN` | Manipuri | ꯃꯩꯇꯩꯂꯣꯟ | ✅ | ❌ | ✅ |
| `ne-IN` | Nepali | नेपाली | ✅ | ❌ | ✅ |
| `sa-IN` | Sanskrit | संस्कृतम् | ✅ | ❌ | ✅ |
| `sat-IN` | Santali | ᱥᱟᱱᱛᱟᱲᱤ | ✅ | ❌ | ✅ |
| `sd-IN` | Sindhi | سنڌي | ✅ | ❌ | ✅ |
| `ur-IN` | Urdu | اردو | ✅ | ❌ | ✅ |

> **Note**: Language codes and capabilities are based on Sarvam's September 2026 documentation. This table must be updated when Sarvam adds or modifies language support. See `AGENTS.md` Rule 1.

### Translation Support Matrix

For any language pair (A → B):

1. **If A=English or B=English**: Direct translation supported via Mayura (10 langs) or Sarvam-Translate (22 langs)
2. **If both A and B are Indic**: Requires English pivot (A → English → B). Two translation calls.
3. **If A=B**: Rejected (same language pair is invalid)

### API Response

```json
// GET /v1/languages
{
  "languages": [
    {
      "code": "hi-IN",
      "name": "Hindi",
      "native_name": "हिन्दी",
      "supports_speech_input": true,
      "supports_translation": true
    },
    {
      "code": "as-IN",
      "name": "Assamese",
      "native_name": "অসমীয়া",
      "supports_speech_input": true,
      "supports_translation": true
    }
  ]
}
```

> **Design note**: The API response intentionally abstracts away Mayura vs. Sarvam-Translate distinction. The client only needs to know whether speech input and translation are supported for a language. Model selection is a backend concern.

## Design Decisions

| Decision | Rationale |
|---|---|
| **BCP-47 codes** | Consistent with Sarvam API; standard for internationalization |
| **Frozen dataclasses** | Languages are immutable reference data |
| **Registry pattern** | Single source of truth; easy to query capabilities |
| **Abstract model flags in API** | Client shouldn't know about Mayura vs. Sarvam-Translate |
| **Validate pairs before API calls** | Fail fast with clear error messages; don't let clients discover limitations via Sarvam errors |

## Failure Modes

| Failure | Impact | Mitigation |
|---|---|---|
| Unknown language code in request | 400 error | Clear `INVALID_LANGUAGE` error with supported list |
| Unsupported pair | 400 error | Clear `UNSUPPORTED_LANGUAGE_PAIR` error |
| Registry out of sync with Sarvam | Requests rejected that could succeed | Regular sync with Sarvam docs; integration tests |

## Future Evolution

1. **Dynamic registry**: Load language support from Sarvam API at startup instead of hardcoding
2. **Per-language quality scores**: Track translation quality per language pair
3. **User language preferences**: Store user's frequent language pairs for faster selection
4. **Language detection**: Use Saaras auto-detection to suggest input language
