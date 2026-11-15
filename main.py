"""Temporary Phase 3 entry point: run ingestion only (replaced by PipelineRunner in Phase 7)."""

import logging

from src.config import settings
from src.ingestor import JobBoardIngestor, save_ndjson, save_sample


def main() -> None:
    """Fetch all pages, write data/raw/jobs.ndjson and context/sample_api.json."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ingestor = JobBoardIngestor(
        api_url=str(settings.api_url),
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
        max_pages=settings.max_pages,
        page_delay_seconds=settings.page_delay_seconds,
    )
    try:
        records = ingestor.fetch_all()
    finally:
        ingestor.close()
    written = save_ndjson(records, settings.raw_dir / "jobs.ndjson")
    sample = save_sample(records, settings.context_dir / "sample_api.json")
    logging.info("Wrote %d raw lines, %d sample records", written, len(sample))


if __name__ == "__main__":
    main()
