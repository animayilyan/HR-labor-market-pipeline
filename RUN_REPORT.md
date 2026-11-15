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
