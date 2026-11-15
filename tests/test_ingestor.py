"""Offline tests for pagination and retries (httpx.MockTransport – no real network)."""

import httpx
import pytest

from src.ingestor import IngestionError, JobBoardIngestor

BASE = "https://api.test/jobs"


def make_ingestor(handler: httpx.MockTransport, sleeps: list[float], max_pages: int = 10) -> JobBoardIngestor:
    """Ingestor wired to a mock transport; sleeps are recorded instead of waited."""
    return JobBoardIngestor(BASE, timeout=1, max_retries=3, max_pages=max_pages, page_delay_seconds=1,
                            client=httpx.Client(transport=handler), sleep=sleeps.append)


def page(n: int, has_next: bool) -> dict[str, object]:
    """One fake API page with a single record."""
    return {"data": [{"slug": f"job-{n}"}],
            "links": {"next": f"{BASE}?page={n + 1}" if has_next else None}, "meta": {"current_page": n}}


def test_follows_links_next_until_null_and_retries_5xx() -> None:
    """A 503 is retried with 1 s backoff; paging stops when links.next is null."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Serve pages 1–3; the first request for page 2 fails with 503."""
        calls.append(str(request.url))
        n = int(request.url.params.get("page", "1"))
        if n == 2 and calls.count(str(request.url)) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=page(n, has_next=n < 3))

    sleeps: list[float] = []
    ingestor = make_ingestor(httpx.MockTransport(handler), sleeps)
    records = ingestor.fetch_all()
    assert [r["slug"] for r in records] == ["job-1", "job-2", "job-3"]
    assert ingestor.stop_reason == "links.next = null"
    assert sleeps == [1, 1, 1]  # page delay, retry backoff (2**0), page delay


def test_stops_at_max_pages() -> None:
    """Never fetches more than max_pages even if links.next keeps going."""
    transport = httpx.MockTransport(lambda r: httpx.Response(
        200, json=page(int(r.url.params.get("page", "1")), has_next=True)))
    ingestor = make_ingestor(transport, [], max_pages=2)
    assert len(ingestor.fetch_all()) == 2
    assert ingestor.stop_reason.startswith("max_pages")


def test_non_retryable_4xx_raises_clear_error() -> None:
    """A 404 is not retried and raises IngestionError naming the status."""
    sleeps: list[float] = []
    ingestor = make_ingestor(httpx.MockTransport(lambda r: httpx.Response(404, text="nope")), sleeps)
    with pytest.raises(IngestionError, match="HTTP 404"):
        ingestor.fetch_all()
    assert sleeps == []
