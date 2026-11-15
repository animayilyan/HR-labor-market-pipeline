# PLAN – Lesson 5 HR Job-Market Pipeline

Claude Code: work through every phase in order. Tick `[x]` as checks pass.
Project folder: `C:\Projects\lesson5_api_pipeline`

---

## Phase 0 – Environment check
- [x] `python --version` (or `py --version`) shows Python 3.11+. Missing → stop, tell the user to install
      Python from python.org with "Add python.exe to PATH" ticked.
- [x] `git --version` works. Missing → stop, tell the user to install Git from git-scm.com.
- [x] `git config user.name` and `git config user.email` return values. Missing → stop and ask the user.
- [x] Internet works: `Invoke-WebRequest https://www.arbeitnow.com/api/job-board-api -UseBasicParsing` returns status 200.

✅ **Done when:** versions are written to RUN_REPORT.md. (No commit yet: the repo starts in Phase 1.)

---

## Phase 1 – Repository and virtual environment
- [x] `git init` (skip if `.git` exists), default branch `main`.
- [x] `python -m venv .venv`
- [x] Install: `httpx polars pydantic pydantic-settings python-dotenv pytest`
- [x] `.venv\Scripts\python.exe -m pip freeze > requirements.txt` (exact pins).
- [x] `.vscode/settings.json` points `python.defaultInterpreterPath` to `.venv\\Scripts\\python.exe`.

✅ **Done when:** `.venv\Scripts\python.exe -c "import httpx, polars, pydantic; print('ok')"` prints `ok`;
`git status` does not list `.venv`.

---

## Phase 2 – Scaffold, config and AI context
Create (files already in the kit: CLAUDE.md, PLAN.md, README.md, .gitignore, .aiignore,
.env.example, context/architecture.md, context/hr_questions.md):
```
main.py
src/__init__.py, config.py, ingestor.py, models.py, transformer.py,
    storage.py, analysis.py, pipeline.py
tests/__init__.py, tests/test_transformer.py
data/raw/  data/processed/  reports/   (add a .gitkeep in each)
context/prompts.md
```
- [x] Copy `.env.example` to `.env` (no secrets needed for this API).
- [x] `src/config.py`: pydantic-settings `Settings` reading `.env`; fields `api_url: HttpUrl`,
      `request_timeout: float`, `max_retries: int`, `max_pages: int`, `page_delay_seconds: float`,
      `db_path: Path`, optional `anthropic_api_key: SecretStr | None = None`.
      Missing or wrong-typed values must fail at startup. Export `settings = Settings()`.

✅ **Done when:** `.venv\Scripts\python.exe -c "from src.config import settings; print(settings.api_url)"`
prints the API URL; `git status` lists neither `.env` nor `.venv`.

---

## Phase 3 – Ingestion (pagination, retries, NDJSON)
`src/ingestor.py` – class `JobBoardIngestor(api_url, timeout, max_retries, max_pages, page_delay_seconds)`:
- `fetch_pages()` generator: start at page 1, follow `links.next` until it is null or `max_pages`
  is reached, yield each page's `data` list. Sleep `page_delay_seconds` between pages.
- Retry timeouts, connection errors, HTTP 429 and 5xx with backoff 1, 2, 4 s (up to `max_retries`);
  raise a clear error on other 4xx. Send a `User-Agent` header naming the project.
- `save_ndjson(records, path)`: one JSON object per line, UTF-8.
- `save_sample(records, path, n=5)`: pretty JSON array, prefer variety (a remote job, an onsite job,
  one with empty tags, one with several job_types, one non-English title if present).
Temporary `main.py` step that runs only ingestion → `data/raw/jobs.ndjson`, `context/sample_api.json`.

✅ **Done when:** raw file line count = number of records the ingestor logged; sample has 5 records;
log shows pages fetched and that it stopped on `links.next = null` or on `max_pages`.

---

## Phase 4 – AI-assisted schema + Pydantic validation (build-time LLM synthesis)
Read ONLY `context/sample_api.json`. Generate `src/models.py`:
- `Job` model with every field in the sample (expected: slug, company_name, title, description,
  remote, url, tags, job_types, location, created_at — confirm against the sample; adapt if different).
  `created_at` arrives as a Unix timestamp → convert to UTC datetime with a field validator.
  Lists default to empty lists. Strip whitespace from strings.
- `validate_records(records) -> tuple[list[Job], list[dict]]`: rejected items keep `slug` (if any)
  and the error text; one bad record never stops the run. Save rejects to `data/processed/rejected.ndjson`.
- Append the exact prompt you used + a 2-line summary to `context/prompts.md`.
- Demonstrate the guardrail in a test: a record with `"remote": "maybe"` lands in rejected.

✅ **Done when:** valid + rejected = raw line count; rejected count reported in RUN_REPORT.md.

---

## Phase 5 – Polars transformation (unnest, explode, fan-out safety)
Follow `context/architecture.md`. In `src/transformer.py` (pure functions, LazyFrame in, DataFrame out):
- `build_jobs(lf)`: one row per slug. Drop duplicate slugs (newest-first feeds shift during paging),
  keep first. Derive `seniority` and `job_function` from the title with `str.contains` regex
  (English AND German keywords, see architecture.md). `tag_count`, `job_type_count` from list lengths.
  `posted_at` datetime. Do not store the HTML description; keep `description_chars` (length) only.
- `build_job_tags(lf)`: explode `tags` → (slug, tag), tag lower-cased and trimmed, empty removed,
  duplicates per slug removed.
- `build_job_types(lf)`: explode `job_types` → (slug, job_type), same cleaning.
- `check_grain(jobs, job_tags, job_types)`: raise if slug not unique in jobs; if
  `sum(tag_count)` ≠ rows in job_tags (after the same cleaning); if any child slug is missing in jobs.

✅ **Done when:** all three checks pass on the full data; counts logged.

---

## Phase 6 – Storage + HR analysis
`src/storage.py` (sqlite3 from the standard library):
- Tables `jobs` (slug PRIMARY KEY), `job_tags` (slug, tag, PK both, FK → jobs),
  `job_types` (slug, job_type, PK both, FK → jobs). Drop + recreate each run; one transaction;
  `executemany`. Also write the three tables to `data/processed/*.parquet`.
`src/analysis.py`: answer every question in `context/hr_questions.md` with Polars from the Parquet files.
Write `reports/summary.md`: one section per question, a small markdown table + a one-line takeaway.
NEVER join job_tags and job_types in the same query (tags × types fan-out); aggregate each separately.

**Done when:** `pipeline.db` and 3 Parquet files exist; `summary.md` has every section with real numbers;
running the pipeline twice gives identical row counts.

---

## Phase 7 – PipelineRunner, tests, README
- `src/pipeline.py`: class `PipelineRunner(settings)` with `run(skip_ingest: bool = False)`:
  ingest → validate → transform → check_grain → store → analyze, logging row counts per stage.
- `main.py`: argparse entry point with `--skip-ingest`.
- `tests/test_transformer.py`: fixture of 3 hand-made records (no network): duplicate slug removed,
  tags exploded and cleaned, seniority/job_function regex (one English, one German title),
  created_at → datetime, `check_grain` raises on mismatched counts, invalid record rejected.
- README.md: complete every section marked TODO; insert the headline findings from summary.md.

**Done when:** `.venv\Scripts\python.exe main.py` completes end to end; `-m pytest` all green;
final commit made; RUN_REPORT.md ends with a plain-language summary for Ani.

---

## Optional – only if `ANTHROPIC_API_KEY` is set in `.env` by the user
`src/llm_fallback.py` (lesson pattern 04, "agentic fallback"): for jobs whose `job_function` is
"Other", send ONLY the titles (max 50, one batched call) to the Anthropic API, require a
Pydantic-validated JSON answer from a fixed category list, temperature 0, and fill the gaps.
If no key is set: skip silently and note "LLM fallback skipped: no key" in RUN_REPORT.md.
