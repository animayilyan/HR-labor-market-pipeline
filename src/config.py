"""Typed application settings loaded from `.env` (fail fast on missing or wrong values)."""

from pathlib import Path

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Pipeline configuration.

    Every required field has no default, so a missing or wrongly typed value in `.env`
    (or the environment) raises a `ValidationError` as soon as the module is imported.
    Relative paths are resolved against the project root, so the pipeline works from
    any current directory.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # `ANTHROPIC_API_KEY=` (blank) counts as "not set"
        extra="ignore",
    )

    api_url: HttpUrl
    request_timeout: float = Field(gt=0)
    max_retries: int = Field(ge=0)
    max_pages: int = Field(ge=1)
    page_delay_seconds: float = Field(ge=0)
    db_path: Path
    anthropic_api_key: SecretStr | None = None

    raw_dir: Path = Path("data/raw")
    processed_dir: Path = Path("data/processed")
    reports_dir: Path = Path("reports")
    context_dir: Path = Path("context")

    @field_validator("db_path", "raw_dir", "processed_dir", "reports_dir", "context_dir")
    @classmethod
    def _resolve_path(cls, value: Path) -> Path:
        """Make relative paths absolute, anchored at the project root."""
        return value if value.is_absolute() else PROJECT_ROOT / value


settings: Settings = Settings()  # type: ignore[call-arg]  # values come from .env
