"""API v1 router.

All versioned API routes are registered on this router with the /api/v1 prefix
(applied in src/main.py). Future endpoints such as /api/v1/translation,
/api/v1/speech/translate, and /api/v1/realtime/translate will be added here.

The health check endpoint is NOT versioned and is registered separately.
"""

from fastapi import APIRouter

router = APIRouter()

# Future route registration:
# from app.api.routes import languages, translation, speech, realtime
# router.include_router(languages.router, tags=["Languages"])
# router.include_router(translation.router, tags=["Translation"])
# router.include_router(speech.router, tags=["Speech"])
# router.include_router(realtime.router, tags=["Realtime"])
