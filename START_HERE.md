# Start here (for Ani)

1. Extract this zip into `C:\Projects` so you get `C:\Projects\lesson5_api_pipeline`
   (if `C:\Projects` doesn't exist, create it first).
2. In VS Code: File → Open Folder → `C:\Projects\lesson5_api_pipeline` → **Yes, I trust the authors**.
3. Open the Claude Code panel and paste the prompt below.
4. Claude Code works through all 7 phases on its own. It only stops if Python or Git is
   missing, if Git doesn't know your name and email, or if a check keeps failing.
5. When it finishes, read `RUN_REPORT.md` and `reports/summary.md`.

## Prompt to paste into Claude Code
```
Read CLAUDE.md, PLAN.md and the files in context/. Then execute PLAN.md from Phase 0 to
Phase 7 without stopping between phases, following every rule in CLAUDE.md. Tick the boxes
in PLAN.md and log each phase in RUN_REPORT.md as you go, and commit after each phase.
Stop only for the reasons CLAUDE.md lists. When done, give me a beginner-friendly summary.
```
