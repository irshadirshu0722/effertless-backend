"""Application configuration using Pydantic Settings.

All configuration is loaded from environment variables. A .env file is
supported for local development (see .env.example for the template).

Never hardcode secrets. See AGENTS.md Rule 7.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    # Application
    app_name: str = "effortless-api"
    app_env: str = "development"
    app_debug: bool = False
    log_level: str = "INFO"

    # Sarvam AI
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_speech_model: str = "saaras:v4"
    sarvam_translation_model: str = "mayura:v1"

    # Authentication: Google Cloud Identity Platform
    gcp_project_id: str = ""
    gcp_identity_web_api_key: str = ""
    auth_check_revoked: bool = True

    # Payments and subscriptions: Cashfree
    cashfree_app_id: str = ""
    cashfree_secret_key: str = ""
    cashfree_webhook_secret: str = ""
    cashfree_environment: str = "sandbox"

    # Tier quotas and free trial defaults
    free_tier_days: int = 7

    # Persistence
    database_url: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "effortless"

    # Cache
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Trail Plan
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton.

    Uses lru_cache so Settings is only instantiated once per process,
    avoiding repeated environment variable reads.
    """
    return Settings()


settings = get_settings()
