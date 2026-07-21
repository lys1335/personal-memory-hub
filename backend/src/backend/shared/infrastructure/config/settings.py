"""Application settings.

Loaded from environment variables and/or .env file via pydantic-settings.
All values have defaults suitable for local development.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AppSettings(BaseSettings):
    """Top-level application configuration.

    Values are loaded from environment variables with prefix ``APP_``,
    falling back to defaults or a .env file.
    """

    model_config = SettingsConfigDict(
        env_prefix="PMH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    NAME: str = "personal-memory-hub"
    VERSION: str = "0.1.0"
    LOG_LEVEL: LogLevel = LogLevel.INFO

    # ------------------------------------------------------------------
    # Database (PostgreSQL / Supabase)
    # ------------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/memory_hub"
    DATABASE_ECHO: bool = False

    # ------------------------------------------------------------------
    # Supabase (optional)
    # ------------------------------------------------------------------
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""

    # ------------------------------------------------------------------
    # Vector / Embeddings
    # ------------------------------------------------------------------
    VECTOR_DIMENSION: int = 1536  # OpenAI ada-002 default

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    SECRET_KEY: str = "changeme"

    # ------------------------------------------------------------------
    # Redis (V2+ placeholder)
    # ------------------------------------------------------------------
    REDIS_URL: str = ""

    # ------------------------------------------------------------------
    # Vector / Embeddings
    # ------------------------------------------------------------------
    EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"

    # ------------------------------------------------------------------
    # LLM / OpenRouter (deferred to D3+)
    # ------------------------------------------------------------------
    OPENROUTER_API_KEY: str = ""

    @property
    def is_supabase(self) -> bool:
        """Return True if Supabase URL is configured."""
        return bool(self.SUPABASE_URL)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """Priority: env vars > .env file > defaults."""
        return (env_settings, dotenv_settings, init_settings)


# Singleton instance — resolved lazily on first access.
_settings_instance: AppSettings | None = None


def get_settings() -> AppSettings:
    """Return the global settings singleton.

    Creates the instance on first call.  Callers should use this
    function rather than importing ``settings`` directly so that
    tests can replace it with ``unittest.mock.patch``.
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = AppSettings()
    return _settings_instance


# Convenience import for direct use (e.g. in Alembic env.py).
settings: AppSettings | None = None
