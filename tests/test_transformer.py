"""Offline tests for validation and transformation (no network, no files)."""

from typing import Any

from src.models import validate_records


def test_invalid_remote_value_is_rejected() -> None:
    """Guardrail: `"remote": "maybe"` is not a boolean, so the record lands in rejected."""
    bad: dict[str, Any] = {
        "slug": "bad-remote-1", "company_name": "ACME", "title": "Analyst",
        "description": "", "remote": "maybe", "url": "https://example.com/x",
        "tags": [], "job_types": [], "location": "Berlin", "created_at": 1794760428,
    }
    valid, rejected = validate_records([bad])
    assert valid == []
    assert len(rejected) == 1
    assert rejected[0]["slug"] == "bad-remote-1"
    assert "remote" in rejected[0]["error"]
