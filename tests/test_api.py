from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from api.main import create_app
from core.message_types import AgentState, ToolCall


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _make_mock_state(
    query: str = "test",
    answer: str = "Test answer.",
    sources: list | None = None,
) -> AgentState:
    state = AgentState(query=query)
    state.final_answer = answer
    state.iterations = 2
    state.sources = sources or [{"title": "Example", "url": "https://example.com"}]
    state.tool_calls_made = [ToolCall(name="web_search", arguments={"query": "test"})]
    return state


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        with patch("api.routes.LLMClient") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.complete = AsyncMock(
                return_value=MagicMock(content="pong")
            )
            mock_cls.return_value = mock_llm

            resp = client.get("/v1/health")
            assert resp.status_code == 200

    def test_health_schema(self, client: TestClient) -> None:
        with patch("api.routes.LLMClient") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.complete = AsyncMock(
                return_value=MagicMock(content="pong")
            )
            mock_cls.return_value = mock_llm

            resp = client.get("/v1/health")
            data = resp.json()
            assert "status" in data
            assert "version" in data
            assert "providers" in data


# ── Ask Endpoint ──────────────────────────────────────────────────────────────

class TestAskEndpoint:
    @patch("api.routes.build_routed_pipeline")
    @patch("api.routes.get_cache")
    def test_ask_auto_success(
        self,
        mock_cache_fn: MagicMock,
        mock_pipeline: MagicMock,
        client: TestClient,
    ) -> None:
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache_fn.return_value = mock_cache

        mock_pipeline.return_value = AsyncMock(
            return_value=_make_mock_state(
                query="What is AI?",
                answer="AI stands for Artificial Intelligence.",
            )
        )()

        resp = client.post(
            "/v1/ask",
            json={"query": "What is AI?", "agent_type": "auto"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert "iterations" in data

    @patch("api.routes.get_cache")
    def test_ask_cache_hit(
        self,
        mock_cache_fn: MagicMock,
        client: TestClient,
    ) -> None:
        cached_data = {
            "request_id": "abc123",
            "query": "cached query",
            "answer": "Cached answer",
            "sources": [],
            "agent_type": "auto",
            "iterations": 1,
            "tools_called": [],
            "model": "gpt-4o",
            "cached": False,
            "metadata": {},
        }
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=cached_data)
        mock_cache.set = AsyncMock()
        mock_cache_fn.return_value = mock_cache

        resp = client.post(
            "/v1/ask",
            json={"query": "cached query", "agent_type": "auto"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is True

    def test_ask_query_too_short(self, client: TestClient) -> None:
        resp = client.post("/v1/ask", json={"query": ""})
        assert resp.status_code == 422

    def test_ask_query_too_long(self, client: TestClient) -> None:
        resp = client.post("/v1/ask", json={"query": "x" * 2001})
        assert resp.status_code == 422

    def test_ask_invalid_agent_type(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/ask",
            json={"query": "test", "agent_type": "nonexistent"},
        )
        assert resp.status_code == 422

    @patch("api.routes.build_routed_pipeline")
    @patch("api.routes.get_cache")
    def test_ask_with_specific_agent_type(
        self,
        mock_cache_fn: MagicMock,
        mock_pipeline: MagicMock,
        client: TestClient,
    ) -> None:
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache_fn.return_value = mock_cache

        with patch("api.routes.build_agent") as mock_build:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(
                return_value=_make_mock_state(answer="React agent answer.")
            )
            mock_build.return_value = mock_agent

            resp = client.post(
                "/v1/ask",
                json={"query": "test question", "agent_type": "react"},
            )
            assert resp.status_code == 200


# ── Models Endpoint ───────────────────────────────────────────────────────────

class TestModelsEndpoint:
    def test_list_models(self, client: TestClient) -> None:
        resp = client.get("/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "openai" in data
        assert "anthropic" in data
        assert isinstance(data["openai"], list)
        assert len(data["openai"]) > 0


# ── Request ID Middleware ─────────────────────────────────────────────────────

class TestMiddleware:
    @patch("api.routes.build_routed_pipeline")
    @patch("api.routes.get_cache")
    def test_request_id_in_response_headers(
        self,
        mock_cache_fn: MagicMock,
        mock_pipeline: MagicMock,
        client: TestClient,
    ) -> None:
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache_fn.return_value = mock_cache

        mock_pipeline.return_value = AsyncMock(
            return_value=_make_mock_state()
        )()

        resp = client.post(
            "/v1/ask",
            json={"query": "test", "agent_type": "auto"},
            headers={"X-Request-ID": "my-custom-id"},
        )
        assert resp.headers.get("X-Request-ID") == "my-custom-id"