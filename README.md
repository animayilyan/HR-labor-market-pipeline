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
TODO (Phase 7): one line per file in src/, tests/, context/, data/, reports/.

## Testing
```powershell
.venv\Scripts\python.exe -m pytest
```

## How AI was used
TODO (Phase 7): build-time schema synthesis from `context/sample_api.json`
(prompts in `context/prompts.md`); optional LLM fallback for job-function classification.

## Headline findings
TODO (Phase 7): 4–6 bullets copied from `reports/summary.md`.
