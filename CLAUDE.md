# Instructions for Claude Code

## Project
Lesson 5 homework (ACAx, AI with Python & Automation APIs): an HR / labor-market analytics
pipeline on the free Arbeitnow job-board API (https://www.arbeitnow.com/api/job-board-api).
Ingest paginated job postings → validate with Pydantic → flatten with Polars →
store in SQLite + Parquet → write an HR analytics summary.

Owner: Ani Mayilyan. Windows 10/11, PowerShell, VS Code.

## How to work
- Follow PLAN.md from Phase 0 to Phase 7 **without stopping between phases**.
- After each phase: run its "Done when" checks, tick its boxes in PLAN.md, append a short
  entry to RUN_REPORT.md (what was built, check results, row counts), then `git add .`
  and `git commit -m "Phase N: <title>"`.
- Stop and ask the user ONLY when:
  1. Python or Git is missing (Phase 0). Never install system software yourself;
     tell the user exactly what to install and stop.
  2. Git user.name / user.email are not set. Ask the user for them; never invent an email.
  3. A "Done when" check still fails after 3 fix attempts. Explain the cause in plain language.
- When everything passes, finish with a plain-language summary for the user
  (beginner level): what each phase produced, the headline HR findings, and where the files are.

## Commands (Windows)
- Always call the venv interpreter directly; no activation needed:
  `.venv\Scripts\python.exe -m pip install ...`
  `.venv\Scripts\python.exe main.py`
  `.venv\Scripts\python.exe -m pytest`
- If `python` is not found, try the launcher `py` (e.g. `py -3 -m venv .venv`).

## Rules
- Never read, print or commit `.env`. Never ask the user to paste a key or password into chat.
- Never read `data/raw/` into your context (it is large). Use `context/sample_api.json`
  for field names and types.
- Read `context/architecture.md` (tables, grain) and `context/hr_questions.md` (analysis)
  before writing transform or analysis code.
- Polars native expressions only: no `map_elements`, no `apply`, no Python row loops over data.
- Type hints and docstrings on every function and class.
- `src/transformer.py` stays pure: no file, network or database I/O (I/O lives in
  ingestor.py, storage.py, pipeline.py), so tests run without internet.
- Be polite to the API (its terms ask users not to abuse it): 1 second pause between pages,
  respect MAX_PAGES from settings, retry with backoff, and credit Arbeitnow in README.md.
- Record every prompt you use to generate schema/parsing code in `context/prompts.md`.
- Keep Armenian/German/English text as UTF-8; don't transliterate.
