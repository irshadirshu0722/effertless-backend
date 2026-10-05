"""Tests for database driver configuration."""

import pytest

from app.core.config import Settings
from app.drivers.database import create_engine


def test_create_engine_requires_database_url() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL"):
        create_engine(Settings(database_url=""))
