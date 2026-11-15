# HR Job-Market Pipeline (Lesson 5)

Ingests live job postings from the free [Arbeitnow job-board API](https://www.arbeitnow.com/),
validates them with Pydantic, flattens them with Polars, stores them in SQLite and Parquet,
and writes an HR analytics summary: who is hiring, which skills are in demand, how many
roles are remote, and at what seniority.

Job data courtesy of [Arbeitnow](https://www.arbeitnow.com/).

## Data flow
API (paged via `links.next`) → `data/raw/jobs.ndjson` → Pydantic validation →
Polars transform (`jobs`, `job_tags`, `job_types`) → SQLite + Parquet → `reports/summary.md`

## Quickstart (Windows PowerShell)
```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe main.py
```
Rerun analysis without calling the API again: `.venv\Scripts\python.exe main.py --skip-ingest`

## Repository map
| Path | What it is |
|---|---|
| `main.py` | Command-line entry point (`--skip-ingest` reuses the raw file, no API calls) |
| `src/config.py` | Typed settings from `.env` (pydantic-settings); fails fast on missing/wrong values |
| `src/ingestor.py` | `JobBoardIngestor`: follows `links.next`, 1 s between pages, `MAX_PAGES` cap, retries with 1-2-4 s backoff; NDJSON + sample writers |
| `src/models.py` | Pydantic `Job` model + `validate_records` (bad records are collected, never fatal) |
| `src/transformer.py` | Pure Polars functions: dedupe, seniority / job-function regex (EN + DE), `jobs` / `job_tags` / `job_types`, `check_grain` |
| `src/storage.py` | SQLite (PK + FK, one transaction, `executemany`) and Parquet writers |
| `src/analysis.py` | Answers the 12 HR questions with Polars and writes `reports/summary.md` |
| `src/pipeline.py` | `PipelineRunner`: ingest → validate → transform → check_grain → store → analyze |
| `tests/test_transformer.py` | Offline tests: dedupe, tag cleaning, EN/DE regex, UTC dates, grain errors, rejected record |
| `tests/test_ingestor.py` | Offline tests with a mock HTTP transport: paging, retry on 503, `MAX_PAGES`, 404 error |
| `context/architecture.md` | Tables, grain and fan-out rules, keyword lists |
| `context/hr_questions.md` | The 12 analysis questions |
| `context/sample_api.json` | 5 varied API records – the only data used to design the schema |
| `context/prompts.md` | Exact prompt(s) used to generate schema/parsing code |
| `data/raw/` | `jobs.ndjson`, one API record per line (git-ignored, regenerated each run) |
| `data/processed/` | `pipeline.db` (SQLite), `jobs/job_tags/job_types.parquet`, `rejected.ndjson`, `run_meta.json` |
| `reports/summary.md` | HR analytics summary: one section per question, table + takeaway |
| `PLAN.md` / `RUN_REPORT.md` | The build plan and the log of what each phase produced |

## Testing
```powershell
.venv\Scripts\python.exe -m pytest
```

## How AI was used
- **Build-time schema synthesis:** Claude Code read only `context/sample_api.json` (5 hand-picked,
  varied records) and generated the Pydantic `Job` model in `src/models.py`. The exact prompt and a short
  summary are in `context/prompts.md`. The model is the guardrail: one bad record is rejected (and logged in
  `data/processed/rejected.ndjson`) without stopping the run; a test proves `"remote": "maybe"` is rejected.
- **Pipeline code** (ingestion, Polars transforms, storage, analysis, tests) was written by Claude Code
  following `PLAN.md` and `CLAUDE.md`, phase by phase, with a commit after each phase.
- **Runtime:** the pipeline itself makes no AI calls. The optional LLM fallback for job-function
  classification (titles left as "Other") was **skipped: no `ANTHROPIC_API_KEY` set**.

## Headline findings
Snapshot 2026-11-15, first 10 API pages (see `reports/summary.md` for all 12 sections):
- **2,505 job postings** from **1,035 companies**, all posted 2026-11-08 → 2026-11-15 (the feed is newest-first).
- **Only 6.4% of jobs are remote**. Marketing (10.7%) and Sales (10.4%) are the most remote-friendly functions, HR & Recruiting the least (3.4%).
- **Engineering is the largest job function** (24.3%), ahead of Sales (11.2%) and Data & Analytics (8.1%); 38.8% of titles match no keyword rule ("Other").
- **Entry-level roles are scarce:** Intern + Junior titles are just 9.0% of postings; 43.7% of titles name no level.
- **Biggest hubs: Paris (14.3%), London (12.7%), Berlin (10.8%)**, then Munich and Zürich. The board is Europe-wide, not Germany-only.
- **Top employer: Doctolib** (56 postings); the top 15 companies post 15.1% of all jobs. Most demanded tags: engineering, sales, remote.
