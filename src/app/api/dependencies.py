"""FastAPI dependency injection providers.

All injectable dependencies (settings, clients, services) are defined here.
Route handlers access them via Depends(). This keeps DI wiring in one place
and out of business logic.

Usage in routes:
    from app.api.dependencies import get_settings
    @router.get("/example")
    async def example(settings: Settings = Depends(get_settings)):
        ...
"""

from app.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]

# Future dependencies will be added here:
#
# def get_sarvam_client(settings: Settings = Depends(get_settings)) -> AsyncSarvamAI:
#     return AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)
#
# def get_speech_provider(client = Depends(get_sarvam_client)) -> SpeechProvider:
#     return SarvamSpeechProvider(client)
#
# def get_translation_provider(client = Depends(get_sarvam_client)) -> TranslationProvider:
#     return SarvamTranslationProvider(client)
