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

## Phase 7 – PipelineRunner, tests, README
- `src/pipeline.py`: `PipelineRunner(settings).run(skip_ingest)` – ingest → validate → transform → check_grain →
  store → analyze, logging row counts per stage; writes `data/processed/run_meta.json`.
  `--skip-ingest` reuses the raw file and the previous run's ingest facts, so reruns are reproducible.
- `main.py`: argparse entry point with `--skip-ingest`.
- Tests (all offline): `tests/test_transformer.py` (7 tests: duplicate slug removed, tags exploded + cleaned,
  EN/DE seniority + job_function, word-boundary guard, created_at → UTC datetime, `check_grain` raises,
  `"remote": "maybe"` rejected) and `tests/test_ingestor.py` (3 tests with `httpx.MockTransport`: paging to
  `links.next = null` with a retried 503, `MAX_PAGES` stop, clear 404 error).
- Added `tzdata==2026.6` to requirements: Windows has no time-zone database, and Polars needs it to hand
  UTC timestamps to Python (2 tests failed without it).
- README: repository map, "How AI was used" and headline findings filled in; Arbeitnow credited.
- **LLM fallback skipped: no key** (`ANTHROPIC_API_KEY` not set in `.env`).
- Checks: `.venv\Scripts\python.exe main.py` completed end to end (fresh API pull: 10 pages, 2,510 records,
  0 rejected, 5 duplicates → **2,505 jobs / 2,755 job_tags / 2,898 job_types**, grain ✅) ✅;
  `main.py --skip-ingest` twice → identical counts and byte-identical `summary.md` ✅;
  `-m pytest` → **10 passed** ✅.
- Note: the live feed changes every hour, so a fresh run can differ slightly from Phase 5/6
  (2,506 jobs then vs 2,505 now) – that is new postings, not a bug.

---

## Summary for Ani (plain language)

**What the pipeline does:** it downloads job ads from the free Arbeitnow job board, checks every ad,
tidies the data into three tables, saves them, and writes an HR report – with one command:
`.venv\Scripts\python.exe main.py`.

| Phase | What it produced |
|---|---|
| 0 | Checked your computer: Python 3.15, Git 2.56 and the internet all work. |
| 1 | A Git project (history of every step) and a private Python "toolbox" (`.venv`) with the exact library versions in `requirements.txt`. |
| 2 | The folder structure and a settings file (`.env`) that the program checks at start-up. |
| 3 | A polite downloader: reads the job board page by page (1 second apart, max 10 pages, retries on errors). Saved 2,510 job ads to `data/raw/jobs.ndjson`. |
| 4 | A "bouncer" for the data (Pydantic): every ad must have the right fields and types. All 2,510 passed; a test shows a fake ad with `remote = "maybe"` is rejected. |
| 5 | Clean tables (Polars): duplicates removed, seniority and job function guessed from the title in English **and** German (e.g. "Werkstudent" → Intern), tags split out. Safety checks confirm nothing is double-counted. |
| 6 | Storage: a SQLite database `data/processed/pipeline.db` plus Parquet files, and the HR report `reports/summary.md`. |
| 7 | One command runs everything; 10 automatic tests; README completed. |

**Headline HR findings (15 Nov 2026 snapshot, 2,505 jobs, 1,035 companies):**
- Only **6.4% of jobs are fully remote** – most roles still expect you on-site or hybrid.
- **Engineering is the biggest field** (24%), then Sales (11%) and Data & Analytics (8%).
- **Entry-level jobs are rare:** internships + junior roles are only 9% of postings.
- The jobs are concentrated in **Paris, London and Berlin**, then Munich and Zürich.
- **Doctolib** posts the most jobs (56). The most common skill tags are engineering, sales and remote.
- Data quality is good (0 rejected, 5 duplicates). The main gap is that 23% of ads give no job type.
  About 39% of titles didn't match any job-function keyword ("Other"); the optional AI step that would
  classify those was skipped because no API key was set.

**Where to look:** `reports/summary.md` (the report), `README.md` (overview), `data/processed/` (database
and Parquet files), `RUN_REPORT.md` (this log), `context/prompts.md` (the AI prompt used for the schema).

## Extra – Optional MySQL export (added on request)
- Found MySQL Server 8.0 running locally (service `MySQL80`, port 3306).
- Added PyMySQL (+ `cryptography` for MySQL 8 `caching_sha2_password` login) to `requirements.txt`.
- `src/config.py`: optional `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` (password as `SecretStr`);
  `src/storage.py`: `write_mysql` (creates `hr_jobs`, utf8mb4 + `utf8mb4_0900_as_cs`, PK/FK like SQLite,
  inserts in one transaction); `src/pipeline.py` runs it only when `MYSQL_PASSWORD` is set and checks
  that MySQL counts equal SQLite counts.
- Without a password: `MySQL skipped (MYSQL_PASSWORD not set in .env)`; tests 10 passed.
