"""
Web scraper — fetches and extracts readable text from public pages.

Production guards (the course version had NONE of these):
* SSRF guard on the requested URL AND on the post-redirect final URL
  (FM-08) — blocks cloud metadata, internal ranges, localhost.
* Streaming fetch with a hard byte cap — a hostile 2GB page costs us at
  most max_response_bytes, not the full download (FM-09).
* Content-Type allowlist — we are a TEXT reader; binaries are rejected
  before parsing.
* HTML parsing off the event loop (asyncio.to_thread) — BeautifulSoup on
  a big page stalls the worker for everyone (FM-11).
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlparse

import structlog
from bs4 import BeautifulSoup

from configs.settings import get_settings
from core.exceptions import ScrapingError
from tools.base_tool import BaseTool, ToolDefinition
from tools.http_client import fetch_bytes_with_cap
from tools.ssrf_guard import ensure_fetchable, validate_response_history

logger = structlog.get_logger(__name__)

_BLOCKED_DOMAINS = frozenset([
    "facebook.com", "instagram.com", "twitter.com", "x.com",
])

_MAX_CONTENT_CHARS = 8_000

_ALLOWED_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


class WebScraperTool(BaseTool):
    """Fetch and extract clean readable text from a public web page."""

    timeout_s = 20.0
    cost_hint = "expensive"  # full page fetch + parse

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="scrape_webpage",
            description=(
                "Fetch and read the full text content of a specific web page. "
                "Use this after web_search to get detailed information from a URL. "
                "Returns cleaned text content from the page."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL of the webpage to scrape",
                    },
                    "extract_links": {
                        "type": "boolean",
                        "description": "Whether to also extract hyperlinks from the page",
                        "default": False,
                    },
                },
                "required": ["url"],
            },
        )

    async def execute(  # type: ignore[override]
        # Plugin-style contract: the REAL parameter contract is the
        # ToolDefinition schema, validated by validate_arguments() before
        # this is ever invoked. Named params are the ergonomic declaration
        # of that schema; Liskov cannot hold across plugins.
        self,
        url: str,
        extract_links: bool = False,
        **_: Any,
    ) -> str:
        # ── Guard 1: SSRF on the requested URL ───────────────────────
        ensure_fetchable(url)

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        if domain in _BLOCKED_DOMAINS:
            return json.dumps(
                {"error": f"Scraping blocked for domain: {domain}"}
            )

        logger.info("scrape_webpage.start", url=url[:120])

        # ── Guard 2: streaming fetch with hard byte cap ──────────────
        body, headers, status, final_url = await fetch_bytes_with_cap(
            url,
            max_bytes=self._settings.max_response_bytes,
            timeout=self._settings.scrape_timeout,
        )

        if status >= 400:
            raise ScrapingError(f"HTTP {status} for {url}")

        # ── Guard 3: re-validate the FINAL URL after redirects ───────
        # A redirect chain can bounce public → 169.254.169.254 (FM-08).
        validate_response_history(final_url)

        # ── Guard 4: content-type allowlist ──────────────────────────
        content_type = (headers.get("content-type") or "").split(";")[0].strip().lower()
        if content_type and content_type not in _ALLOWED_CONTENT_TYPES:
            return json.dumps({
                "error": f"Unsupported content type: {content_type}. "
                         "Only HTML and plain text can be read.",
                "url": url,
            })

        html = body.decode("utf-8", errors="replace")

        # ── Guard 5: parse off the event loop ────────────────────────
        text, links = await asyncio.to_thread(self._parse_html, html)

        result: dict[str, Any] = {
            "url": url,
            "content": text[:_MAX_CONTENT_CHARS],
            "content_length": len(text),
            "truncated": len(text) > _MAX_CONTENT_CHARS,
        }
        if extract_links:
            result["links"] = links[:20]

        return json.dumps(result, indent=2)

    def _parse_html(self, html: str) -> tuple[str, list[str]]:
        """CPU-bound parsing — runs in a worker thread (FM-11)."""
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "advertisement", "noscript", "iframe"]):
            tag.decompose()

        links = [
            a.get("href", "")
            for a in soup.find_all("a", href=True)
            if a.get("href", "").startswith("http")
        ]

        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id=re.compile(r"content|main|article", re.I))
            or soup.find(class_=re.compile(r"content|main|article|post", re.I))
            or soup.body
        )

        raw_text = main.get_text(separator="\n") if main else soup.get_text()
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        return "\n".join(lines), links
