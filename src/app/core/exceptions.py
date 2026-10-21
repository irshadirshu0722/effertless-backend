"""Application exception hierarchy and FastAPI error handlers.

Domain and application exceptions are defined here to decouple business
logic from FastAPI's HTTPException. The infrastructure and domain layers
raise these exceptions; the API layer catches them via registered handlers.

Error response format follows docs/api/errors.md:
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable description.",
        "request_id": "req_abc123"
    }
}
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------


class AppError(Exception):
    def __init__(
        self,
        code: str = "INTERNAL_SERVER_ERROR",
        message: str = "An unexpected error occurred.",
        status_code: int = 500,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Authentication and authorization errors
# ---------------------------------------------------------------------------


class AuthenticationRequiredError(AppError):
    """Raised when a protected operation is requested without credentials."""

    def __init__(self):
        super().__init__(
            code="AUTHENTICATION_REQUIRED",
            message="Authentication is required. Include an Authorization: Bearer token.",
            status_code=401,
        )


class InvalidAuthTokenError(AppError):
    """Raised when a bearer token is invalid, expired, or malformed."""

    def __init__(self):
        super().__init__(
            code="INVALID_AUTH_TOKEN",
            message="The authentication token is invalid or expired.",
            status_code=401,
        )


class AuthTokenRevokedError(AppError):
    """Raised when a bearer token was valid but has been revoked."""

    def __init__(self):
        super().__init__(
            code="AUTH_TOKEN_REVOKED",
            message="The authentication token has been revoked.",
            status_code=401,
        )


class AuthorizationFailedError(AppError):
    """Raised when an authenticated user is not allowed to perform an action."""

    def __init__(self):
        super().__init__(
            code="AUTHORIZATION_FAILED",
            message="The authenticated user is not allowed to perform this action.",
            status_code=403,
        )


# ---------------------------------------------------------------------------
# Subscription and usage quota errors
# ---------------------------------------------------------------------------


class AudioExceedsTierLimitError(AppError):
    """Raised when requested audio duration exceeds the plan tier limit."""

    def __init__(self, requested_seconds: float, max_seconds: int):
        super().__init__(
            code="AUDIO_EXCEEDS_TIER_LIMIT",
            message=(
                f"Audio duration of {requested_seconds:.1f}s exceeds your tier limit of {max_seconds}s. "
                "Upgrade your plan for longer recordings."
            ),
            status_code=400,
        )


class DailyQuotaExceededError(AppError):
    """Raised when the user has exhausted their daily request allowance."""

    def __init__(self, daily_limit: int):
        super().__init__(
            code="DAILY_QUOTA_EXCEEDED",
            message=f"Daily request quota of {daily_limit} reached. Quota resets at midnight UTC.",
            status_code=429,
        )


class SubscriptionRequiredError(AppError):
    """Raised when a subscription or active trial is required to perform an action."""

    def __init__(
        self, message: str = "Active subscription or trial required to access this feature."
    ):
        super().__init__(
            code="SUBSCRIPTION_REQUIRED",
            message=message,
            status_code=402,
        )


class PlanNotFoundError(AppError):
    """Raised when the requested subscription plan does not exist."""

    def __init__(self, identifier: str):
        super().__init__(
            code="PLAN_NOT_FOUND",
            message=f"Subscription plan '{identifier}' not found or inactive.",
            status_code=404,
        )


class ActiveSubscriptionError(AppError):
    """Raised when user already has an active subscription to the requested plan."""

    def __init__(self, message: str = "You already have an active subscription to this plan."):
        super().__init__(
            code="ACTIVE_SUBSCRIPTION_EXISTS",
            message=message,
            status_code=400,
        )


class InvalidWebhookSignatureError(AppError):
    """Raised when an incoming webhook signature is invalid or tampered with."""

    def __init__(self):
        super().__init__(
            code="INVALID_WEBHOOK_SIGNATURE",
            message="Invalid webhook signature.",
            status_code=401,
        )


class SubscriptionPaymentError(AppError):
    """Raised when payment gateway rejects a subscription checkout operation."""

    def __init__(self, detail: str = "Payment gateway error."):
        super().__init__(
            code="PROVIDER_UNAVAILABLE",
            message=f"Payment provider error: {detail}",
            status_code=502,
        )


# ---------------------------------------------------------------------------
# Language errors
# ---------------------------------------------------------------------------


class InvalidLanguageError(AppError):
    """Raised when a language code is not recognized."""

    def __init__(self, language_code: str):
        super().__init__(
            code="INVALID_LANGUAGE",
            message=f"Language code '{language_code}' is not recognized.",
            status_code=400,
        )


class UnsupportedLanguagePairError(AppError):
    """Raised when a source→target language combination is not supported."""

    def __init__(self, source: str, target: str):
        super().__init__(
            code="UNSUPPORTED_LANGUAGE_PAIR",
            message=f"Translation from {source} to {target} is not currently supported.",
            status_code=400,
        )


# ---------------------------------------------------------------------------
# Input validation errors
# ---------------------------------------------------------------------------


class TextTooLongError(AppError):
    def __init__(self, max_length: int):
        super().__init__(
            code="TEXT_TOO_LONG",
            message=f"Input text exceeds the maximum length of {max_length} characters.",
            status_code=400,
        )


class InvalidAudioError(AppError):
    def __init__(self, reason: str = "Audio data is malformed or unreadable."):
        super().__init__(code="INVALID_AUDIO", message=reason, status_code=400)


class AudioTooLargeError(AppError):
    def __init__(self, max_mb: int = 5):
        super().__init__(
            code="AUDIO_TOO_LARGE",
            message=f"Audio file exceeds the maximum size of {max_mb} MB.",
            status_code=400,
        )


class UnsupportedAudioFormatError(AppError):
    def __init__(self):
        super().__init__(
            code="UNSUPPORTED_AUDIO_FORMAT",
            message="The audio format is not supported.",
            status_code=400,
        )


# ---------------------------------------------------------------------------
# Provider errors
# ---------------------------------------------------------------------------


class SpeechRecognitionError(AppError):
    def __init__(self, detail: str = "Speech recognition failed."):
        super().__init__(
            code="SPEECH_RECOGNITION_FAILED",
            message=detail,
            status_code=500,
        )


class TranslationError(AppError):
    def __init__(self, detail: str = "Translation failed."):
        super().__init__(
            code="TRANSLATION_FAILED",
            message=detail,
            status_code=500,
        )


class ProviderRateLimitedError(AppError):
    def __init__(self, provider: str = "provider"):
        super().__init__(
            code="PROVIDER_RATE_LIMITED",
            message="The AI service is temporarily rate-limited. Please retry shortly.",
            status_code=503,
        )


class ProviderUnavailableError(AppError):
    def __init__(self, provider: str = "provider"):
        super().__init__(
            code="PROVIDER_UNAVAILABLE",
            message="The AI service is temporarily unavailable.",
            status_code=503,
        )


class ProviderTimeoutError(AppError):
    def __init__(self, provider: str = "provider"):
        super().__init__(
            code="REQUEST_TIMEOUT",
            message="The request timed out waiting for the AI service.",
            status_code=504,
        )


# ---------------------------------------------------------------------------
# Exception handler registration
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers on the FastAPI app."""

    def request_id_for(request: Request) -> str:
        return getattr(request.state, "request_id", None) or request.headers.get(
            "X-Request-Id", "unknown"
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """Convert AppError subclasses to the standard error response format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id_for(request),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Return the public validation error without exposing internals."""
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "request_id": request_id_for(request),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unhandled exceptions. Never expose internals."""
        import logging

        logger = logging.getLogger("core.exceptions")
        logger.exception("Unhandled exception: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "request_id": request_id_for(request),
                }
            },
        )
