"""Pydantic schema for one Arbeitnow job posting (generated from context/sample_api.json).

See `context/prompts.md` (Prompt 1) for the exact prompt used to generate this module.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError, field_validator


class Job(BaseModel):
    """One job posting as returned in the API's `data` list.

    Guardrails: whitespace is stripped from every string, `remote` must be a real boolean,
    `created_at` (Unix seconds) becomes a UTC datetime, and missing / null lists become `[]`.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore", frozen=True)

    slug: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    remote: StrictBool
    url: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    job_types: list[str] = Field(default_factory=list)
    location: str = ""
    created_at: datetime

    @field_validator("tags", "job_types", mode="before")
    @classmethod
    def _none_to_empty_list(cls, value: Any) -> Any:
        """Treat a JSON `null` list as an empty list."""
        return [] if value is None else value

    @field_validator("description", "location", mode="before")
    @classmethod
    def _none_to_empty_str(cls, value: Any) -> Any:
        """Treat a JSON `null` optional text field as an empty string."""
        return "" if value is None else value

    @field_validator("created_at", mode="before")
    @classmethod
    def _unix_to_utc(cls, value: Any) -> datetime:
        """Convert a Unix timestamp (seconds) to a timezone-aware UTC datetime."""
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"created_at must be a Unix timestamp (int seconds), got {value!r}")
        if value < 0:
            raise ValueError(f"created_at must not be negative, got {value!r}")
        return datetime.fromtimestamp(value, tz=UTC)


def validate_records(records: list[dict[str, Any]]) -> tuple[list[Job], list[dict[str, Any]]]:
    """Validate records one by one; return (valid jobs, rejected items).

    A rejected item is `{"index", "slug", "error"}` so it can be traced back to the raw
    file. One bad record never stops the run.
    """
    valid: list[Job] = []
    rejected: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        try:
            valid.append(Job.model_validate(record))
        except ValidationError as exc:
            slug = record.get("slug") if isinstance(record, dict) else None
            errors = "; ".join(
                f"{'.'.join(str(p) for p in err['loc']) or '<record>'}: {err['msg']}"
                for err in exc.errors(include_url=False)
            )
            rejected.append({"index": index, "slug": slug, "error": errors})
    return valid, rejected
