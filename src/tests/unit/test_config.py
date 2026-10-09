"""Tests for environment-backed application settings."""

from app.core.config import Settings


def test_default_app_name_matches_product() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "effortless-api"
