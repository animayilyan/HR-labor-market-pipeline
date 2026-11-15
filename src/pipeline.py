"""End-to-end orchestration: ingest → validate → transform → check_grain → store → analyze."""

import logging
from datetime import UTC, datetime
from typing import Any

from src.analysis import headline_findings, write_summary
from src.config import Settings
from src.ingestor import JobBoardIngestor, read_ndjson, save_ndjson, save_sample
from src.models import validate_records
from src.storage import read_json, write_json, write_mysql, write_parquet, write_sqlite
from src.transformer import build_job_tags, build_job_types, build_jobs, check_grain, jobs_to_lazyframe

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Run the whole pipeline with one `Settings` object, logging row counts per stage."""

    def __init__(self, settings: Settings) -> None:
        """Keep the settings and derive the file locations used by every stage."""
        self.settings = settings
        self.raw_path = settings.raw_dir / "jobs.ndjson"
        self.sample_path = settings.context_dir / "sample_api.json"
        self.rejected_path = settings.processed_dir / "rejected.ndjson"
        self.meta_path = settings.processed_dir / "run_meta.json"
        self.summary_path = settings.reports_dir / "summary.md"

    def _ingest(self) -> dict[str, Any]:
        """Fetch every page from the API and write the raw NDJSON file; return ingest metadata."""
        s = self.settings
        ingestor = JobBoardIngestor(str(s.api_url), s.request_timeout, s.max_retries,
                                    s.max_pages, s.page_delay_seconds)
        try:
            records = ingestor.fetch_all()
        finally:
            ingestor.close()
        save_ndjson(records, self.raw_path)
        if not self.sample_path.exists():  # the sample is the schema reference; keep it stable
            save_sample(records, self.sample_path)
        return {"ingested_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "pages_fetched": ingestor.pages_fetched, "stop_reason": ingestor.stop_reason}

    def _previous_ingest_meta(self) -> dict[str, Any]:
        """For `--skip-ingest`: reuse the last run's ingest facts (or the raw file's timestamp)."""
        previous = read_json(self.meta_path)
        keys = ("ingested_at", "pages_fetched", "stop_reason")
        if all(k in previous for k in keys):
            return {k: previous[k] for k in keys}
        mtime = datetime.fromtimestamp(self.raw_path.stat().st_mtime, UTC)
        return {"ingested_at": mtime.isoformat(timespec="seconds"),
                "pages_fetched": "n/a", "stop_reason": "unknown (no previous run metadata)"}

    def run(self, skip_ingest: bool = False) -> dict[str, Any]:
        """Execute all stages; return the run metadata (row counts per stage)."""
        s = self.settings
        if skip_ingest:
            if not self.raw_path.exists():
                raise FileNotFoundError(f"{self.raw_path} not found – run once without --skip-ingest")
            meta = self._previous_ingest_meta()
            logger.info("Stage ingest: skipped (--skip-ingest), reusing %s", self.raw_path.name)
        else:
            meta = self._ingest()
            logger.info("Stage ingest: %s pages (%s)", meta["pages_fetched"], meta["stop_reason"])

        raw = read_ndjson(self.raw_path)
        logger.info("Stage raw: %d records", len(raw))

        valid, rejected = validate_records(raw)
        save_ndjson(rejected, self.rejected_path)
        logger.info("Stage validate: %d valid, %d rejected", len(valid), len(rejected))

        lf = jobs_to_lazyframe(valid)
        tables = {"jobs": build_jobs(lf), "job_tags": build_job_tags(lf), "job_types": build_job_types(lf)}
        duplicates = len(valid) - tables["jobs"].height
        logger.info("Stage transform: %d duplicate slugs removed; jobs=%d, job_tags=%d, job_types=%d",
                    duplicates, *(t.height for t in tables.values()))

        grain = check_grain(**tables)
        logger.info("Stage check_grain: passed %s", grain)

        if s.anthropic_api_key is None:
            logger.info("LLM fallback skipped: no key")
            meta["llm_fallback"] = "skipped: no key"
        else:  # optional lesson step; not part of the required pipeline
            logger.info("LLM fallback: key present but src/llm_fallback.py is not implemented – skipped")
            meta["llm_fallback"] = "skipped: not implemented"

        db_counts = write_sqlite(s.db_path, tables)
        write_parquet(s.processed_dir, tables)
        logger.info("Stage store: SQLite %s + 3 Parquet files in %s", db_counts, s.processed_dir.name)

        if s.mysql_enabled and s.mysql_password is not None:
            mysql_counts = write_mysql(tables, s.mysql_host, s.mysql_port, s.mysql_user,
                                       s.mysql_password.get_secret_value(), s.mysql_database)
            if mysql_counts != db_counts:
                raise RuntimeError(f"MySQL counts {mysql_counts} differ from SQLite {db_counts}")
            logger.info("Stage store: MySQL %s@%s:%d/%s %s", s.mysql_user, s.mysql_host,
                        s.mysql_port, s.mysql_database, mysql_counts)
            meta["mysql"] = f"written to database {s.mysql_database}"  # no host: this file is committed
        else:
            logger.info("Stage store: MySQL skipped (MYSQL_PASSWORD not set in .env)")
            meta["mysql"] = "skipped: no password"

        meta |= {"raw_records": len(raw), "valid_records": len(valid),
                 "rejected_records": len(rejected), "duplicates_removed": duplicates,
                 "tables": db_counts}
        write_json(self.meta_path, meta)

        sections = write_summary(s.processed_dir, self.summary_path, meta)
        logger.info("Stage analyze: %d sections → %s", len(sections), self.summary_path)
        for line in headline_findings(sections):
            logger.info("  • %s", line.replace("**", ""))
        return meta
