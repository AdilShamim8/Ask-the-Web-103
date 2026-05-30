from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from configs.settings import get_settings
from core.exceptions import ScrapingError
from tools.base_tool import BaseTool, ToolDefinition

logger = structlog.get_logger(__name__)

_BLOCKED_DOMAINS = frozenset([
    "facebook.com", "instagram.com", "twitter.com", "x.com",
])

_MAX_CONTENT_CHARS = 8000


class WebScraperTool(BaseTool):
    """
    Fetches and extracts clean readable text from a web page URL.
    Strips ads, navigation, scripts, and boilerplate.
    """

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

    async def execute(
        self,
        url: str,
        extract_links: bool = False,
        **_: Any,
    ) -> str:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        if domain in _BLOCKED_DOMAINS:
            return f"Scraping blocked for domain: {domain}"

        if parsed.scheme not in ("http", "https"):
            raise ScrapingError(f"Invalid URL scheme: {parsed.scheme}")

        logger.info("scrape_webpage.start", url=url)

        try:
            async with httpx.AsyncClient(
                timeout=self._settings.scrape_timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; AskWebAgent/1.0; "
                        "+https://github.com/example/ask-the-web)"
                    )
                },
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

        except httpx.HTTPStatusError as exc:
            raise ScrapingError(f"HTTP {exc.response.status_code} for {url}") from exc
        except httpx.RequestError as exc:
            raise ScrapingError(f"Request failed for {url}: {exc}") from exc

        text, links = self._parse_html(html, url)

        result: dict[str, Any] = {
            "url": url,
            "content": text[:_MAX_CONTENT_CHARS],
            "content_length": len(text),
            "truncated": len(text) > _MAX_CONTENT_CHARS,
        }

        if extract_links:
            result["links"] = links[:20]

        import json
        return json.dumps(result, indent=2)

    def _parse_html(self, html: str, url: str) -> tuple[str, list[str]]:
        soup = BeautifulSoup(html, "lxml")

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "advertisement", "noscript", "iframe"]):
            tag.decompose()

        # Extract links before cleaning
        links = [
            a.get("href", "")
            for a in soup.find_all("a", href=True)
            if a.get("href", "").startswith("http")
        ]

        # Try to find main content
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id=re.compile(r"content|main|article", re.I))
            or soup.find(class_=re.compile(r"content|main|article|post", re.I))
            or soup.body
        )

        raw_text = main.get_text(separator="\n") if main else soup.get_text()

        # Clean up whitespace
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        clean = "\n".join(lines)

        return clean, links