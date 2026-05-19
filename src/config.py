"""Centralised application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings validated from environment variables.

    All required fields raise a clear ``ConfigurationError`` on startup if absent.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Azure OpenAI
    azure_openai_endpoint: str = Field(..., description="Azure OpenAI resource endpoint URL")
    azure_openai_key: str = Field(..., description="Azure OpenAI API key")
    azure_openai_api_version: str = Field(
        default="2024-10-21", description="Azure OpenAI API version"
    )
    azure_openai_deployment_mini: str = Field(
        default="gpt-4o-mini", description="Deployment name for the cheap/fast model"
    )
    azure_openai_deployment_4o: str = Field(
        default="gpt-4o", description="Deployment name for the reasoning/writing model"
    )

    # Bing Search (optional — code falls back to DuckDuckGo when absent)
    bing_search_key: str | None = Field(default=None, description="Bing Search v7 API key")
    bing_search_endpoint: str = Field(
        default="https://api.bing.microsoft.com/v7.0/search",
        description="Bing Search v7 endpoint",
    )

    # Job platform APIs
    adzuna_app_id: str = Field(..., description="Adzuna application ID")
    adzuna_app_key: str = Field(..., description="Adzuna application key")
    jooble_api_key: str = Field(..., description="Jooble API key")

    # Telegram
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    telegram_chat_id: str = Field(..., description="Telegram chat ID for notifications")

    # Logging
    log_json: bool = Field(
        default=False, description="Emit JSON logs (true in CI) instead of pretty console output"
    )


class ConfigurationError(RuntimeError):
    """Raised when required environment variables are missing."""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the validated application settings (cached singleton).

    Raises:
        ConfigurationError: If any required environment variable is missing.
    """
    try:
        return Settings()  # type: ignore[call-arg]  # pydantic-settings reads env vars
    except ValidationError as exc:
        missing = [e["loc"][0] for e in exc.errors() if e["type"] == "missing"]
        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(str(m) for m in missing)}. "
                "Copy .env.example to .env and fill in the values."
            ) from exc
        raise ConfigurationError(str(exc)) from exc
