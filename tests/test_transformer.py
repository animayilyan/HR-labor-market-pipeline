"""Offline tests for validation and transformation (no network, no files)."""

from datetime import UTC, datetime
from typing import Any

import polars as pl
import pytest

from src.models import validate_records
from src.transformer import (
    GrainError,
    build_job_tags,
    build_job_types,
    build_jobs,
    check_grain,
    jobs_to_lazyframe,
)

TS = 1794760428  # a Unix timestamp from the API sample


def record(slug: str, title: str, **overrides: Any) -> dict[str, Any]:
    """Build one hand-made API record with sensible defaults."""
    base: dict[str, Any] = {
        "slug": slug, "company_name": "ACME GmbH", "title": title, "description": "<p>Hallo</p>",
        "remote": False, "url": f"https://example.com/{slug}", "tags": [], "job_types": [],
        "location": "Berlin", "created_at": TS,
    }
    return base | overrides


@pytest.fixture
def raw_records() -> list[dict[str, Any]]:
    """Three hand-made records: an English job, its duplicate slug, and a German job."""
    return [
        record("senior-data-analyst-1", "  Senior Data Analyst  ", remote=True,
               tags=["  Python ", "python", "", "SQL"], job_types=["Full Time", "full time "]),
        record("senior-data-analyst-1", "Senior Data Analyst (older copy)", tags=["Excel"]),
        record("werkstudent-hr-2", "Werkstudent Personalwesen (m/w/d)",
               tags=["Human Resources"], job_types=["hilfstätigkeit / student"], created_at=TS - 86400),
    ]


@pytest.fixture
def lf(raw_records: list[dict[str, Any]]) -> pl.LazyFrame:
    """Validated fixture records as a LazyFrame."""
    valid, rejected = validate_records(raw_records)
    assert rejected == []
    return jobs_to_lazyframe(valid)


def test_duplicate_slug_removed_keeps_first(lf: pl.LazyFrame) -> None:
    """Two records share a slug → one row, and it is the first (newest) one."""
    jobs = build_jobs(lf)
    assert jobs.height == 2
    assert jobs.get_column("slug").n_unique() == 2
    first = jobs.filter(pl.col("slug") == "senior-data-analyst-1").row(0, named=True)
    assert first["title"] == "Senior Data Analyst"  # whitespace stripped by the model
    assert first["remote"] is True


def test_tags_exploded_and_cleaned(lf: pl.LazyFrame) -> None:
    """Tags are trimmed, lower-cased, de-duplicated per job; empty tags removed."""
    tags = build_job_tags(lf).sort(["slug", "tag"])
    assert tags.rows() == [
        ("senior-data-analyst-1", "python"),
        ("senior-data-analyst-1", "sql"),
        ("werkstudent-hr-2", "human resources"),
    ]
    types = build_job_types(lf).sort(["slug", "job_type"])
    assert types.rows() == [
        ("senior-data-analyst-1", "full time"),
        ("werkstudent-hr-2", "hilfstätigkeit / student"),  # UTF-8 kept, no transliteration
    ]
    jobs = build_jobs(lf).sort("slug")
    assert jobs.get_column("tag_count").to_list() == [2, 1]
    assert jobs.get_column("job_type_count").to_list() == [1, 1]


def test_seniority_and_job_function_english_and_german(lf: pl.LazyFrame) -> None:
    """English 'Senior Data Analyst' and German 'Werkstudent Personalwesen' are classified."""
    jobs = build_jobs(lf).sort("slug")
    assert jobs.select("seniority", "job_function").rows() == [
        ("Senior", "Data & Analytics"),
        ("Intern", "HR & Recruiting"),
    ]


def test_short_keywords_use_word_boundaries() -> None:
    """'hr' must not match inside 'three'; 'intern' must not match 'international'."""
    valid, _ = validate_records([record("a", "Three International Drivers"), record("b", "HR Manager")])
    jobs = build_jobs(jobs_to_lazyframe(valid)).sort("slug")
    assert jobs.select("seniority", "job_function").rows() == [
        ("Mid / unspecified", "Other"),
        ("Lead", "HR & Recruiting"),
    ]


def test_created_at_becomes_utc_datetime(lf: pl.LazyFrame) -> None:
    """Unix seconds → timezone-aware UTC datetime in `posted_at`."""
    jobs = build_jobs(lf).sort("slug")
    assert jobs.schema["posted_at"] == pl.Datetime("us", "UTC")
    assert jobs.get_column("posted_at")[0] == datetime.fromtimestamp(TS, tz=UTC)
    assert "description" not in jobs.columns
    assert jobs.get_column("description_chars")[0] == len("<p>Hallo</p>")


def test_check_grain_passes_then_raises_on_mismatch(lf: pl.LazyFrame) -> None:
    """Valid tables pass; dropping a tag row or adding an orphan raises GrainError."""
    jobs, tags, types = build_jobs(lf), build_job_tags(lf), build_job_types(lf)
    assert check_grain(jobs, tags, types) == {"jobs": 2, "job_tags": 3, "job_types": 2}
    with pytest.raises(GrainError, match="tag_count"):
        check_grain(jobs, tags.head(2), types)
    with pytest.raises(GrainError, match="not unique"):
        check_grain(pl.concat([jobs, jobs.head(1)]), tags, types)


def test_invalid_remote_value_is_rejected() -> None:
    """Guardrail: `"remote": "maybe"` is not a boolean, so the record lands in rejected."""
    good = record("ok-1", "Data Engineer")
    bad = record("bad-remote-1", "Analyst", remote="maybe")
    valid, rejected = validate_records([good, bad])
    assert [job.slug for job in valid] == ["ok-1"]
    assert len(rejected) == 1
    assert rejected[0]["slug"] == "bad-remote-1"
    assert "remote" in rejected[0]["error"]
