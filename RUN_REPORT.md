# RUN REPORT – Lesson 5 HR Job-Market Pipeline

Run date: 2026-11-15. Project folder: `C:\Users\urdob\OneDrive\Desktop\AI IN DATA ANALYTICS\lesson5_api_pipeline`
(the kit was opened from the Desktop/OneDrive folder rather than `C:\Projects`; everything works the same).

## Phase 0 – Environment check
| Check | Result |
|---|---|
| Python | **3.15.2** at `C:\Users\urdob\.local\bin\python3.15.exe` (uv-managed). `python` / `py` are not on PATH (only the Microsoft Store stub), so this interpreter is used to create `.venv`; all later commands call `.venv\Scripts\python.exe`. Anaconda 3.9.13 also present but too old. |
| Git | **2.56.1.windows.1** (`C:\Program Files\Git\cmd\git.exe`; not on the PowerShell PATH, used via Git Bash) |
| git user.name / user.email | Not set. Asked Ani → set **locally for this repo only** in Phase 1 (`Ani Mayilyan`). |
| Internet / API | `Invoke-WebRequest https://www.arbeitnow.com/api/job-board-api` → **200** |

Result: ✅ passed (no commit yet; the repo starts in Phase 1).

## Phase 1 – Repository and virtual environment
- `git init -b main`; identity set with `git config --local` (user.name `Ani Mayilyan`, email from Ani's answer).
- `.venv` created with Python 3.15.2; installed httpx 0.28.1, polars 2.1.0, pydantic 2.14.3,
  pydantic-settings 2.16.3, python-dotenv 1.2.4, pytest 9.2.0 → `requirements.txt` (21 exact pins).
- `.vscode/settings.json` → `python.defaultInterpreterPath` = `.venv\Scripts\python.exe`.
- Checks: `import httpx, polars, pydantic` → `ok` ✅; `git status` does not list `.venv` ✅.

## Phase 2 – Scaffold, config and AI context
- Created `main.py`, `src/` (config, ingestor, models, transformer, storage, analysis, pipeline),
  `tests/`, `data/raw/`, `data/processed/`, `reports/` (with `.gitkeep`), `context/prompts.md`.
- `.env` copied from `.env.example` (not read, not committed).
- `src/config.py`: pydantic-settings `Settings` (HttpUrl, float/int with range checks, Path resolved
  against the project root, optional `SecretStr` key; blank key = not set).
- Checks: `print(settings.api_url)` → `https://www.arbeitnow.com/api/job-board-api` ✅;
  `API_URL=not-a-url` and `MAX_PAGES=abc` both fail at import with a ValidationError ✅;
  `git status` lists neither `.env` nor `.venv` ✅.

## Phase 3 – Ingestion (pagination, retries, NDJSON)
- `src/ingestor.py`: `JobBoardIngestor` (follows `links.next`, 1 s pause between pages, `MAX_PAGES` cap,
  retries timeouts / connection errors / 429 / 5xx with 1-2-4 s backoff, clear `IngestionError` on other 4xx,
  project `User-Agent`), `save_ndjson`, `read_ndjson`, `save_sample` (variety-first).
- Temporary `main.py` ran ingestion only.
- Log: pages 1–5 had 300 records, page 6 had 210, pages 7–10 had 200 → **10 pages, 2,510 records**,
  stopped on **`max_pages = 10` reached** (the feed had more pages).
- Checks: `data/raw/jobs.ndjson` = **2,510 lines** = logged record count ✅; `context/sample_api.json` has
  **5 records** (remote, on-site, empty tags, several job_types, German titles) ✅.

## Phase 4 – AI-assisted schema + Pydantic validation
- Read only `context/sample_api.json`; confirmed the 10 expected fields (slug, company_name, title,
  description, remote, url, tags, job_types, location, created_at) – no differences.
- `src/models.py`: `Job` (strict bool `remote`, Unix → UTC `created_at`, `[]` defaults, stripped strings,
  extra keys ignored) + `validate_records` (per-record, rejects keep index, slug and error text).
- Prompt + 2-line summary recorded in `context/prompts.md` (Prompt 1).
- Guardrail test `test_invalid_remote_value_is_rejected` (`"remote": "maybe"` → rejected) ✅ passes.
- Checks: **2,510 valid + 0 rejected = 2,510 raw lines** ✅. Rejected count: **0**
  (`data/processed/rejected.ndjson` written, empty).

## Phase 5 – Polars transformation
- `src/transformer.py` (pure, LazyFrame in → DataFrame out, native expressions only):
  `jobs_to_lazyframe`, `dedupe_slugs`, `build_jobs`, `build_job_tags`, `build_job_types`, `check_grain`.
- Seniority / job_function regex follow architecture.md (English + German, first match wins, `\b` on
  short English words). Two small, documented refinements: `(^|[^g])leit(ung|er)` so "Begleiter"
  (companion) is not a lead, and `steuer([^u]|$)` so "Steuerungstechnik" is not Finance. Added
  `account manager` to Sales (Key/Strategic Account Managers were landing in "Other").
- Counts on the full data: 2,510 valid → **4 duplicate slugs removed → 2,506 jobs**;
  **2,756 job_tags** rows; **2,899 job_types** rows.
- `check_grain` ✅ all pass: slug unique; sum(tag_count) = 2,756 = job_tags rows;
  sum(job_type_count) = 2,899 = job_types rows; no orphan child slugs.
- job_function: Other 972, Engineering 608, Sales 280, Data & Analytics 202, Marketing 149,
  HR & Recruiting 88, Finance 84, Customer Support 65, Design 58.

## Phase 6 – Storage + HR analysis
- `src/storage.py`: SQLite via `sqlite3` – `jobs` (slug PK), `job_tags` / `job_types` (composite PK, FK → jobs,
  `PRAGMA foreign_keys = ON`); drop + recreate in **one transaction** (`BEGIN … COMMIT`, rollback on error),
  `executemany`; also writes `data/processed/{jobs,job_tags,job_types}.parquet` and `run_meta.json`.
- `src/analysis.py`: all 12 questions from `hr_questions.md` answered with Polars from the Parquet files;
  markdown tables rendered with native Polars string expressions. `job_tags` and `job_types` are never
  joined together (Q10 joins only `job_tags` ⋈ `jobs`, which is 1:N). Locations are free text, so a
  `normalize_city` expression merges variants (e.g. "9th arrondissement of Paris" → Paris, Zurich → Zürich,
  "Remote job"/"Homeoffice" → Remote / home office). Takeaways are computed from the numbers.
- Checks (run twice with a temporary driver script outside the repo): `pipeline.db` + 3 Parquet files exist ✅;
  `reports/summary.md` has all 12 sections + headline findings with real numbers ✅;
  both runs → jobs **2,506**, job_tags **2,756**, job_types **2,899** (identical) ✅.
