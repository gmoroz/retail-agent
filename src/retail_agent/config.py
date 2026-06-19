"""Runtime configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven secrets, endpoints and project identifiers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    llm_base_url: str = Field(description="OpenAI-compatible chat completions base URL.")
    llm_api_key: SecretStr = Field(description="Bearer key for the chat completions endpoint.")
    llm_model: str = Field(description="Model slug used by the chat client.")

    openrouter_api_key: SecretStr = Field(description="OpenRouter key for embeddings, the A/B sweep and the judge.")

    google_cloud_project: str = Field(description="GCP project id used for BigQuery billing.")
    google_application_credentials: str | None = Field(
        default=None,
        description="Path to a service-account JSON. When unset, ADC is used.",
    )

    db_uri: str = Field(description="Postgres connection string (psycopg format).")

    @property
    def sqlalchemy_url(self) -> str:
        """Postgres URL in the SQLAlchemy ``postgresql+psycopg://`` form.

        ``db_uri`` is stored native (``postgresql://``) so the bare-psycopg
        LangGraph checkpointer connects unchanged; SQLAlchemy consumers (Alembic
        env, Golden-bucket engine) select the psycopg3 driver here (ADR-021).
        """

        if self.db_uri.startswith("postgresql://"):
            return "postgresql+psycopg://" + self.db_uri[len("postgresql://") :]
        return self.db_uri


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached :class:`Settings` singleton.

    Tests override it by clearing the cache (``get_settings.cache_clear()``) after
    monkeypatching the environment.
    """

    return Settings()
