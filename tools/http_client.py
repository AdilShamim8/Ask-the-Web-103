"""
Shared outbound HTTP pool for all tools.

The original tools each created a fresh ``httpx.AsyncClient`` per request —
connection churn (TCP+TLS handshake per call), ephemeral-port pressure at
scale, and +50ms latency per external call (FMEA FM-18). This module gives
every tool one shared, keep-alive-pooled client, configured from settings.

Lifecycle: the client is created lazily on first use and closed by the
FastAPI lifespan shutdown hook (api/main.py). Tests get a stub via
``set_http_client()``.
"""

from __future__ import annotations

import httpx
import structlog

from configs.settings import get_settings

logger = structlog.get_logger(__name__)

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return the shared pooled client (created on first use)."""
    global _client
    if _client is None or _client.is_closed:
        settings = get_settings()
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=settings.scrape_timeout,
                write=10.0,
                pool=5.0,
            ),
            limits=httpx.Limits(
                max_connections=settings.http_pool_max_connections,
                max_keepalive_connections=settings.http_pool_max_keepalive,
                keepalive_expiry=30.0,
            ),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "AskWebAgent/2.0 (+https://github.com/AdilShamim8/Ask-the-Web-103)"
                ),
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            },
        )
        logger.debug("http_client.created", pool=settings.http_pool_max_connections)
    return _client


def set_http_client(client: httpx.AsyncClient | None) -> None:
    """Test seam: inject a mock/transport-backed client."""
    global _client
    _client = client


async def close_http_client() -> None:
    """Shutdown hook — closes keep-alive connections cleanly."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        logger.debug("http_client.closed")
    _client = None


async def fetch_bytes_with_cap(
    url: str,
    *,
    max_bytes: int,
    timeout: float | None = None,
) -> tuple[bytes, httpx.Headers, int, str]:
    """
    GET ``url`` streaming with a hard byte cap (FMEA FM-09).

    Streams in chunks and ABORTS as soon as the body exceeds ``max_bytes``,
    so a hostile 2GB page costs us at most ``max_bytes`` of memory and
    bandwidth, not the whole download-then-check disaster.

    Returns (body_bytes_capped, headers, status_code, final_url).
    ``final_url`` reflects redirects — callers MUST re-validate it with
    ``ssrf_guard.validate_response_history`` (FM-08: redirect-to-internal).
    """
    client = get_http_client()
    chunks: list[bytes] = []
    received = 0

    async with client.stream("GET", url, timeout=timeout) as response:
        final_url = str(response.url)

        # Content-Length pre-check: refuse before downloading anything.
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            response.close()
            from core.observability import TOOL_CALLS

            TOOL_CALLS.labels(tool="fetch_url", outcome="truncated").inc()
            return b"", response.headers, response.status_code, final_url

        async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
            received += len(chunk)
            if received > max_bytes:
                logger.warning(
                    "http.body_cap_exceeded", url=url[:120], max_bytes=max_bytes
                )
                break
            chunks.append(chunk)

        return b"".join(chunks), response.headers, response.status_code, final_url
