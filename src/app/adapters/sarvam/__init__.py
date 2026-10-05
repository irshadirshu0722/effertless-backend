"""Sarvam AI infrastructure boundary.

All Sarvam SDK usage is isolated within this package. The application and
domain layers interact with Sarvam through protocols defined in app/domain/.

See:
- docs/architecture/provider-abstraction.md
- docs/ai/sarvam-model-strategy.md
- skills/sarvam-ai/SKILL.md
- AGENTS.md Rule 1 (never invent Sarvam APIs)
- AGENTS.md Rule 2 (never expose provider details to domain)

Future contents:
- client.py          — AsyncSarvamAI wrapper with config
- speech_provider.py — SarvamSpeechProvider (implements SpeechProvider protocol)
- translation_provider.py — SarvamMayuraProvider, SarvamTranslateProvider
- mapper.py          — Sarvam response → domain model mapping
- errors.py          — Sarvam exception → domain exception mapping
"""
