"""Application configuration using Pydantic settings."""

import os
from typing import List, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = Field(default="dev", description="Application environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    postgres_dsn: SecretStr = Field(
        default=...,
        description="PostgreSQL connection string",
        alias="POSTGRES_DSN",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # Yandex Cloud
    yc_folder_id: str = Field(
        default=...,
        description="Yandex Cloud folder ID",
        alias="YC_FOLDER_ID",
    )
    yc_oauth_token: SecretStr = Field(
        default=...,
        description="Yandex Cloud OAuth token",
        alias="YC_OAUTH_TOKEN",
    )

    # Yandex GPT
    yandex_gpt_model: str = Field(
        default="gpt://foundationModels/text/latest",
        description="Yandex GPT model URI",
    )

    # Yandex SpeechKit
    yandex_stt_model: str = Field(
        default="general",
        description="Yandex STT model",
    )
    yandex_tts_voice: str = Field(
        default="ermil",
        description="Yandex TTS voice for Russian",
    )
    yandex_tts_voice_en: str = Field(
        default="en_US",
        description="Yandex TTS voice for English",
    )

    # Yandex Vision
    yandex_vision_ocr_model: str = Field(
        default="ocr",
        description="Yandex Vision OCR model",
    )

    # Yandex Translate
    yandex_translate_folder_id: str = Field(
        default=...,
        description="Yandex Translate folder ID",
    )

    # Telegram
    tg_bot_token: Optional[SecretStr] = Field(
        default=None,
        description="Telegram bot token",
    )
    tg_allowed_user_ids: List[int] = Field(
        default_factory=list,
        description="Allowed Telegram user IDs",
    )

    # HH.ru
    hh_api_token: Optional[SecretStr] = Field(
        default=None,
        description="HH.ru API token",
    )

    # LinkedIn (optional)
    linkedin_client_id: Optional[str] = Field(
        default=None,
        description="LinkedIn client ID",
    )
    linkedin_client_secret: Optional[SecretStr] = Field(
        default=None,
        description="LinkedIn client secret",
    )
    linkedin_access_token: Optional[SecretStr] = Field(
        default=None,
        description="LinkedIn access token",
    )

    # Audio I/O
    audio_input_device: str = Field(
        default="default",
        description="Audio input device",
    )
    audio_output_device: str = Field(
        default="default",
        description="Audio output device",
    )
    hotword: str = Field(
        default="Мага",
        description="Voice activation hotword",
    )

    # Voice Pipeline
    voice_pipeline_timeout: int = Field(
        default=30,
        description="Voice pipeline timeout in seconds",
    )
    voice_pipeline_buffer_size: int = Field(
        default=4096,
        description="Audio buffer size",
    )
    voice_pipeline_sample_rate: int = Field(
        default=16000,
        description="Audio sample rate",
    )

    # LLM
    llm_max_tokens: int = Field(
        default=4096,
        description="Maximum tokens for LLM responses",
    )
    llm_temperature: float = Field(
        default=0.7,
        description="LLM temperature parameter",
    )
    llm_timeout: int = Field(
        default=60,
        description="LLM request timeout in seconds",
    )

    # HTTP Client
    http_timeout: int = Field(
        default=30,
        description="HTTP client timeout in seconds",
    )
    http_max_retries: int = Field(
        default=3,
        description="HTTP client max retries",
    )
    http_backoff_factor: float = Field(
        default=2.0,
        description="HTTP client backoff factor",
    )

    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(
        default=60,
        description="Rate limit requests per minute",
    )
    rate_limit_burst_size: int = Field(
        default=10,
        description="Rate limit burst size",
    )

    # Metrics
    metrics_port: int = Field(
        default=9090,
        description="Prometheus metrics port",
    )

    # OpenTelemetry (optional)
    otel_service_name: str = Field(
        default="ai-maga",
        description="OpenTelemetry service name",
    )
    otel_exporter_otlp_endpoint: Optional[str] = Field(
        default=None,
        description="OpenTelemetry OTLP endpoint",
    )

    @field_validator("tg_allowed_user_ids", mode="before")
    @classmethod
    def parse_allowed_user_ids(cls, v):
        """Parse comma-separated user IDs."""
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    @property
    def is_prod(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "prod"

    @property
    def is_dev(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() == "dev"

    @property
    def database_url(self) -> str:
        """Get database URL from secret."""
        return self.postgres_dsn.get_secret_value()

    @property
    def yc_token(self) -> str:
        """Get Yandex Cloud token from secret."""
        return self.yc_oauth_token.get_secret_value()


# Global settings instance
settings = AppSettings()
