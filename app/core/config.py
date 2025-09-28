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
        env_prefix_parsing=True,  # Enable prefix parsing
    )

    # Application
    app_env: str = Field(default="dev", description="Application environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database - support both Railway and local formats
    postgres_dsn: Optional[SecretStr] = Field(
        default=None,
        description="PostgreSQL connection string",
        alias="POSTGRES_DSN",
    )
    database_url: Optional[SecretStr] = Field(
        default=None,
        description="Database URL (Railway format)",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # Yandex Cloud
    yc_folder_id: str = Field(
        default="",
        description="Yandex Cloud folder ID",
        alias="YC_FOLDER_ID",
    )
    yc_oauth_token: SecretStr = Field(
        default="",
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
        default="",
        description="Yandex Translate folder ID",
    )

    # Telegram
    tg_bot_token: Optional[SecretStr] = Field(
        default=None,
        description="Telegram bot token",
    )
    tg_allowed_user_ids: Optional[str] = Field(
        default=None,
        description="Allowed Telegram user IDs (comma-separated)",
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

    # NLU
    nlp_confidence_threshold: float = Field(
        default=0.5,
        description="Confidence threshold for intent detection",
    )

    # Orchestrator
    orch_max_steps: int = Field(
        default=6,
        description="Maximum steps in action plan",
    )
    orch_time_budget_ms: int = Field(
        default=800,
        description="Time budget for orchestration in milliseconds",
    )

    # OCR
    ocr_max_image_mb: int = Field(
        default=5,
        description="Maximum image size for OCR in MB",
    )
    ocr_rate_per_min: int = Field(
        default=30,
        description="OCR rate limit per minute",
    )

    # Translation
    translate_default_lang: str = Field(
        default="en",
        description="Default target language for translation",
    )

    # Telegram
    tg_webhook_url: Optional[str] = Field(
        default=None,
        description="Telegram webhook URL",
    )

    # HH.ru
    hh_base_url: str = Field(
        default="https://api.hh.ru",
        description="HH.ru API base URL",
    )
    hh_default_area: int = Field(
        default=1,
        description="Default area ID for HH.ru search",
    )

    # LinkedIn
    linkedin_mode: str = Field(
        default="operator",
        description="LinkedIn integration mode: official or operator",
    )

    # Scheduler
    sched_max_retries: int = Field(
        default=5,
        description="Maximum retries for scheduled tasks",
    )
    sched_jitter_ms: int = Field(
        default=250,
        description="Jitter for scheduled tasks in milliseconds",
    )

    @property
    def tg_allowed_user_ids_list(self) -> List[int]:
        """Get parsed list of allowed user IDs."""
        if self.tg_allowed_user_ids:
            return [int(x.strip()) for x in self.tg_allowed_user_ids.split(",") if x.strip()]
        return []

    @property
    def is_prod(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "prod"

    @property
    def is_dev(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() == "dev"

    @property
    def db_dsn(self) -> str:
        """Get database DSN, preferring Railway format."""
        if self.database_url and self.database_url.get_secret_value():
            return self.database_url.get_secret_value()
        elif self.postgres_dsn and self.postgres_dsn.get_secret_value():
            return self.postgres_dsn.get_secret_value()
        else:
            return "postgresql+psycopg://maga:password@localhost:5432/ai_maga"

    @property
    def yc_token(self) -> str:
        """Get Yandex Cloud token from secret."""
        return self.yc_oauth_token.get_secret_value()


# Global settings instance
settings = AppSettings()
