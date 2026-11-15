"""Command-line entry point for the HR job-market pipeline.

Usage (Windows PowerShell):
    .venv\\Scripts\\python.exe main.py                # fetch from the API, then everything else
    .venv\\Scripts\\python.exe main.py --skip-ingest  # reuse data/raw/jobs.ndjson (no API calls)
"""

import argparse
import logging
import sys

from src.config import settings
from src.pipeline import PipelineRunner


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line flags."""
    parser = argparse.ArgumentParser(description="Arbeitnow HR job-market pipeline")
    parser.add_argument("--skip-ingest", action="store_true",
                        help="reuse data/raw/jobs.ndjson instead of calling the API")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the pipeline; return a process exit code."""
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # page logs come from src.ingestor
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # German/French text in logs on Windows consoles
        sys.stderr.reconfigure(encoding="utf-8")
    meta = PipelineRunner(settings).run(skip_ingest=args.skip_ingest)
    logging.info("Done: %s", meta["tables"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
