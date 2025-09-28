"""Unit tests for configuration."""

import pytest
from pydantic import ValidationError

from app.core.config import AppSettings


def test_app_settings_defaults():
    """Test default settings."""
    settings = AppSettings()

    assert settings.app_env == "dev"
    assert settings.log_level == "INFO"
    assert settings.hotword == "Мага"
    assert settings.voice_pipeline_timeout == 30


def test_app_settings_validation():
    """Test settings validation."""
    # Valid settings
    settings = AppSettings(
        app_env="prod",
        yc_folder_id="test-folder",
        yc_oauth_token="test-token",
    )

    assert settings.app_env == "prod"
    assert settings.yc_folder_id == "test-folder"
    assert settings.is_prod is True

    # Invalid settings should raise ValidationError
    with pytest.raises(ValidationError):
        AppSettings(llm_temperature=2.0)  # Should be <= 1.0 or similar constraint


def test_telegram_user_ids_parsing():
    """Test parsing of Telegram user IDs."""
    settings = AppSettings(tg_allowed_user_ids="123, 456 , 789")

    assert settings.tg_allowed_user_ids == [123, 456, 789]


def test_properties():
    """Test computed properties."""
    settings = AppSettings(
        app_env="prod",
        postgres_dsn="postgresql://user:pass@host:5432/db"
    )

    assert settings.is_prod is True
    assert settings.is_dev is False
    assert "postgresql" in settings.database_url
