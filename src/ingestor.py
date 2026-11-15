"""Polite, paginated ingestion from the Arbeitnow job-board API (network + file I/O)."""

import json
import logging
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

USER_AGENT: str = "lesson5-hr-pipeline/1.0 (ACAx student homework; polite paging, 1 req/s)"
RETRYABLE_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class IngestionError(RuntimeError):
    """Raised when the API cannot be read (non-retryable 4xx, or retries exhausted)."""


class JobBoardIngestor:
    """Fetch job postings page by page, following `links.next`.

    Politeness rules (the API terms ask users not to abuse it): a fixed pause between
    pages, a hard `max_pages` cap, retries with exponential backoff (1, 2, 4 s ...),
    and a `User-Agent` that names the project.
    """

    def __init__(
        self,
        api_url: str,
        timeout: float,
        max_retries: int,
        max_pages: int,
        page_delay_seconds: float,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Store settings; `client` and `sleep` can be injected for offline tests."""
        self.api_url = api_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_pages = max_pages
        self.page_delay_seconds = page_delay_seconds
        self._client = client or httpx.Client(
            timeout=timeout, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        self._sleep = sleep
        self.pages_fetched: int = 0
        self.records_fetched: int = 0
        self.stop_reason: str = "not started"

    def _get_json(self, url: str) -> dict[str, Any]:
        """GET one URL with retries on timeouts, connection errors, 429 and 5xx."""
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.get(url)
            except httpx.TransportError as exc:  # timeouts + connection errors
                problem = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    return response.json()
                if response.status_code not in RETRYABLE_STATUS:
                    raise IngestionError(
                        f"API returned HTTP {response.status_code} for {url} "
                        f"(not retryable): {response.text[:200]}"
                    )
                problem = f"HTTP {response.status_code}"
            if attempt == self.max_retries:
                raise IngestionError(f"Giving up on {url} after {attempt + 1} attempts ({problem})")
            backoff = 2**attempt  # 1, 2, 4, ...
            logger.warning("%s on %s – retry %d/%d in %ss", problem, url, attempt + 1,
                           self.max_retries, backoff)
            self._sleep(backoff)
        raise IngestionError(f"Unreachable retry state for {url}")  # pragma: no cover

    def fetch_pages(self) -> Iterator[list[dict[str, Any]]]:
        """Yield each page's `data` list, from page 1 until `links.next` is null or `max_pages`."""
        url: str | None = self.api_url
        self.pages_fetched = 0
        self.records_fetched = 0
        while url is not None:
            if self.pages_fetched > 0:
                self._sleep(self.page_delay_seconds)
            payload = self._get_json(url)
            records: list[dict[str, Any]] = payload.get("data") or []
            self.pages_fetched += 1
            self.records_fetched += len(records)
            logger.info("Page %d: %d records (url=%s)", self.pages_fetched, len(records), url)
            yield records

            next_url = (payload.get("links") or {}).get("next")
            if not next_url:
                self.stop_reason = "links.next = null"
                break
            if self.pages_fetched >= self.max_pages:
                self.stop_reason = f"max_pages = {self.max_pages} reached"
                break
            url = next_url
        logger.info("Stopped after %d pages, %d records: %s",
                    self.pages_fetched, self.records_fetched, self.stop_reason)

    def fetch_all(self) -> list[dict[str, Any]]:
        """Collect every record from `fetch_pages()` into one list."""
        return [record for page in self.fetch_pages() for record in page]

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()


def save_ndjson(records: list[dict[str, Any]], path: Path) -> int:
    """Write one JSON object per line (UTF-8, non-ASCII kept as-is); return lines written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.writelines(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    return len(records)


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    """Read an NDJSON file back into a list of dicts (blank lines ignored)."""
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _is_non_english(title: str) -> bool:
    """Heuristic: German/other-language titles carry umlauts, ß, non-ASCII or a gender tag."""
    lowered = title.lower()
    return (not title.isascii()) or any(m in lowered for m in ("(m/w/d)", "(w/m/d)", "(m/f/d)"))


def save_sample(records: list[dict[str, Any]], path: Path, n: int = 5) -> list[dict[str, Any]]:
    """Save `n` varied records as a pretty JSON array (used as the schema reference).

    Preference order: a remote job, an on-site job, one with empty tags, one with several
    job_types, one non-English title. Remaining slots are filled with the first unused records.
    """
    predicates: list[Callable[[dict[str, Any]], bool]] = [
        lambda r: r.get("remote") is True,
        lambda r: r.get("remote") is False,
        lambda r: not r.get("tags"),
        lambda r: len(r.get("job_types") or []) >= 2,
        lambda r: _is_non_english(str(r.get("title", ""))),
    ]
    chosen: list[dict[str, Any]] = []
    used: set[str] = set()
    for predicate in predicates:
        match = next((r for r in records if predicate(r) and r.get("slug") not in used), None)
        if match is not None:
            chosen.append(match)
            used.add(match.get("slug", ""))
    chosen.extend(r for r in records if r.get("slug") not in used)
    sample = chosen[:n]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sample
