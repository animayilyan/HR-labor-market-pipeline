# Prompts used to generate schema / parsing code

Every prompt used to generate schema or parsing code is recorded here verbatim,
followed by a 2-line summary of what it produced.

---

## Prompt 1 – Pydantic `Job` model from the API sample (Phase 4, 2026-11-15)
Model: Claude Opus 5.5 (Claude Code, build-time synthesis). Input: ONLY `context/sample_api.json`
(5 varied records); `data/raw/` was not read.

```text
You are generating src/models.py for a Python 3.15 data pipeline. Use Pydantic v2.
Input: context/sample_api.json — a JSON array of 5 job postings from the Arbeitnow
job-board API. Read only this file; do not assume fields that are not in it.

1. List every key in the sample with its JSON type and whether it was ever empty.
2. Write a `Job(BaseModel)` with one field per key, using the narrowest safe type:
   - strings stripped of surrounding whitespace (model_config str_strip_whitespace=True);
     `slug`, `title`, `company_name`, `url` must be non-empty;
   - `remote` is a strict boolean: reject strings such as "maybe" or "yes";
   - `tags` and `job_types` are list[str] that default to an empty list (null → []);
   - `created_at` arrives as a Unix timestamp in seconds → convert to a timezone-aware
     UTC datetime in a field validator; reject booleans, strings and negative numbers;
   - ignore unknown extra keys so a new API field does not break the run.
3. Write `validate_records(records: list[dict]) -> tuple[list[Job], list[dict]]` that
   validates one record at a time, so one bad record never stops the run. Each rejected
   item is a dict with `slug` (or None), the record index, and the readable error text.
4. Type hints and docstrings on every function and class. Keep German/English text as
   UTF-8 (no transliteration). No file, network or database I/O in this module.
```

**Summary:** produced `src/models.py` with a 10-field `Job` model (strict `remote`, UTC `created_at`
validator, empty-list defaults, whitespace stripping) and a per-record `validate_records` that collects rejects instead of failing.
The guardrail is tested in `tests/test_transformer.py` (`"remote": "maybe"` → rejected).
