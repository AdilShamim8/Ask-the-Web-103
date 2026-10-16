from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.exceptions import ToolExecutionError
from core.message_types import ToolCall
from tools import build_default_registry
from tools.calculator import CalculatorTool, _safe_eval
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry
from tools.web_search import WebSearchTool
from tools.web_scraper import WebScraperTool


# ── Calculator ────────────────────────────────────────────────────────────────

class TestSafeEval:
    def test_basic_arithmetic(self) -> None:
        assert _safe_eval("2 + 2") == 4.0
        assert _safe_eval("10 - 3") == 7.0
        assert _safe_eval("6 * 7") == 42.0
        assert _safe_eval("15 / 4") == 3.75

    def test_power(self) -> None:
        assert _safe_eval("2 ** 10") == 1024.0

    def test_math_functions(self) -> None:
        import math
        assert abs(_safe_eval("sqrt(144)") - 12.0) < 1e-9
        assert abs(_safe_eval("sin(pi/2)") - 1.0) < 1e-9
        assert abs(_safe_eval("log(e)") - 1.0) < 1e-9

    def test_blocks_import(self) -> None:
        with pytest.raises(ToolExecutionError):
            _safe_eval("__import__('os').system('ls')")

    def test_blocks_unknown_names(self) -> None:
        with pytest.raises(ToolExecutionError):
            _safe_eval("open('/etc/passwd').read()")

    def test_nested_expression(self) -> None:
        result = _safe_eval("sqrt(pow(3, 2) + pow(4, 2))")
        assert abs(result - 5.0) < 1e-9


@pytest.mark.asyncio
class TestCalculatorTool:
    async def test_integer_output(self) -> None:
        tool = CalculatorTool()
        result = await tool.execute(expression="6 * 7")
        assert result == "42"

    async def test_float_output(self) -> None:
        tool = CalculatorTool()
        result = await tool.execute(expression="1 / 3")
        assert "0.333" in result

    async def test_schema_name(self) -> None:
        tool = CalculatorTool()
        assert tool.name == "calculator"

    async def test_schema_has_required(self) -> None:
        tool = CalculatorTool()
        assert "expression" in tool.definition.parameters["required"]


# ── Tool Registry ─────────────────────────────────────────────────────────────

class TestToolRegistry:
    def test_register_and_get(self) -> None:
        registry = ToolRegistry()
        tool = CalculatorTool()
        registry.register(tool)
        assert "calculator" in registry
        assert registry.get("calculator") is tool

    def test_get_schemas_format(self) -> None:
        registry = build_default_registry()
        schemas = registry.get_schemas()
        assert all("type" in s for s in schemas)
        assert all(s["type"] == "function" for s in schemas)
        assert all("function" in s for s in schemas)

    def test_tool_not_found(self) -> None:
        from core.exceptions import ToolNotFoundError
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError):
            registry.get("nonexistent_tool")

    def test_len(self) -> None:
        registry = build_default_registry()
        assert len(registry) == 4


# ── Tool Executor ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestToolExecutor:
    async def test_execute_one_success(self) -> None:
        registry = build_default_registry()
        executor = ToolExecutor(registry)
        call = ToolCall(name="calculator", arguments={"expression": "2+2"})
        result = await executor.execute_one(call)
        assert not result.is_error
        assert result.content == "4"

    async def test_execute_one_error(self) -> None:
        registry = build_default_registry()
        executor = ToolExecutor(registry)
        call = ToolCall(name="calculator", arguments={"expression": "bad expr!!!"})
        result = await executor.execute_one(call)
        assert result.is_error
        assert "ERROR" in result.content

    async def test_execute_parallel(self) -> None:
        registry = build_default_registry()
        executor = ToolExecutor(registry)
        calls = [
            ToolCall(name="calculator", arguments={"expression": f"{i}*{i}"})
            for i in range(1, 5)
        ]
        results = await executor.execute_parallel(calls)
        assert len(results) == 4
        assert results[0].content == "1"
        assert results[1].content == "4"
        assert results[2].content == "9"
        assert results[3].content == "16"

    async def test_execute_unknown_tool(self) -> None:
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        call = ToolCall(name="ghost_tool", arguments={})
        result = await executor.execute_one(call)
        assert result.is_error


# ── Web Search ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestWebSearchTool:
    async def test_schema_structure(self) -> None:
        tool = WebSearchTool()
        schema = tool.definition.to_openai_format()
        assert schema["function"]["name"] == "web_search"
        assert "query" in schema["function"]["parameters"]["required"]

    @patch("tools.web_search.httpx.AsyncClient")
    async def test_tavily_success(self, mock_client_cls: MagicMock) -> None:
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json = MagicMock(return_value={
            "results": [
                {
                    "title": "Test Title",
                    "url": "https://example.com",
                    "content": "Test content snippet",
                    "score": 0.9,
                }
            ]
        })

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        with patch("tools.web_search.get_settings") as mock_settings:
            from configs.settings import SearchProvider
            settings = MagicMock()
            settings.search_provider = SearchProvider.TAVILY
            settings.tavily_api_key.get_secret_value.return_value = "test-key"
            settings.search_timeout = 15.0
            mock_settings.return_value = settings

            tool = WebSearchTool()
            result = await tool.execute(query="test query", num_results=1)
            data = json.loads(result)
            assert "results" in data
            assert data["results"][0]["title"] == "Test Title"


# ── Web Scraper ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestWebScraperTool:
    async def test_blocked_domain(self) -> None:
        tool = WebScraperTool()
        result = await tool.execute(url="https://facebook.com/some/page")
        assert "blocked" in result.lower()

    async def test_invalid_scheme(self) -> None:
        from core.exceptions import ScrapingError
        tool = WebScraperTool()
        with pytest.raises(ScrapingError):
            await tool.execute(url="ftp://example.com/file")

    def test_parse_html_extracts_text(self) -> None:
        tool = WebScraperTool()
        html = """
        <html>
          <body>
            <nav>Navigation junk</nav>
            <main>
              <h1>Main Title</h1>
              <p>Important content here.</p>
            </main>
            <footer>Footer junk</footer>
          </body>
        </html>
        """
        text, links = tool._parse_html(html, "https://example.com")
        assert "Main Title" in text
        assert "Important content here" in text
        assert "Navigation junk" not in text
        assert "Footer junk" not in text