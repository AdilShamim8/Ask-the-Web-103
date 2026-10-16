"""
API tests — v2 contracts.

Key differences from the 1.0 suite:
* Health is CHEAP: no LLM mocking needed (the old suite had to fake a
  provider call for every probe — the exact production bug we fixed).
* Dependencies are overridden via FastAPI's dependency_overrides — no
  patching module internals of api.routes.
* Cache interplay now goes through the singleflight-aware fake.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import pytest
from fastapi.testclient import TestClient

from api import dependencies as deps
from api.main import create_app
from core.message_types import AgentState, ToolCall


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
    state.metadata["usage"] = {
        "llm_calls": 2, "input_tokens": 100, "output_tokens": 50,
        "tool_calls": 1, "web_searches": 1, "pages_fetched": 0,
        "estimated_cost_usd": 0.001,
    }
    return state


class FakeCache:
    """Singleflight-aware cache fake: get→None, compute passthrough."""

    def __init__(self, preloaded: dict[str, Any] | None = None) -> None:
        self.preloaded = preloaded or {}
        self.set_calls: list[str] = []

    async def get(self, query, agent_type, model):
        return self.preloaded.get(query.lower().strip())

    async def set(self, query, agent_type, model, data, ttl=None):
        self.set_calls.append(query)

    async def get_or_compute(self, query, agent_type, model, compute):
        if query.lower().strip() in self.preloaded:
            return self.preloaded[query.lower().strip()], False
        value = await compute()
        self.preloaded[query.lower().strip()] = value
        return value, True

    async def invalidate(self, *a):
        pass

    async def close(self):
        pass


def _make_factory(state: AgentState):
    def _factory(agent_type, **kwargs):
        class FakeAgent:
            async def run(self, q, **kw):
                return state
        return FakeAgent()
    return _factory


@pytest.fixture
def app():
    application = create_app()
    # Default overrides for every test: fake cache + fake agents.
    fake_cache = FakeCache()

    def _cache_override():
        return fake_cache

    def _factory_override():
        return _make_factory(_make_mock_state())

    application.dependency_overrides[deps.get_cache] = _cache_override
    application.dependency_overrides[deps.get_agent_factory] = _factory_override
    return application


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Health (cheap by contract) ────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200_without_any_provider_calls(self, client):
        """Liveness must NEVER depend on external providers (the 1.0
        version made a paid LLM call per probe)."""
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_healthz_alias(self, client):
        assert client.get("/v1/healthz").status_code == 200

    def test_health_schema(self, client):
        data = client.get("/v1/health").json()
        assert "status" in data
        assert "version" in data
        assert "providers" in data

    def test_readyz_reports_shape(self, client):
        data = client.get("/v1/readyz").json()
        assert "status" in data
        assert "redis" in data
        assert "tools" in data


# ── Ask ───────────────────────────────────────────────────────────────────────

class TestAskEndpoint:
    def test_ask_specific_agent_success(self, client):
        resp = client.post(
            "/v1/ask", json={"query": "What is AI?", "agent_type": "react"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Test answer."
        assert data["agent_type"] == "react"
        assert data["api_version"] == "2.0"

    def test_ask_returns_usage_disclosure(self, client, monkeypatch):
        """ADR-05: responses disclose what the request consumed."""
        import api.routes as routes_mod

        async def fake_pipeline(query, model=None):
            return _make_mock_state()

        monkeypatch.setattr(routes_mod, "build_routed_pipeline", fake_pipeline)
        data = client.post(
            "/v1/ask", json={"query": "cost question"},
        ).json()
        assert data["usage"]["llm_calls"] == 2
        assert data["usage"]["estimated_cost_usd"] > 0

    def test_ask_cache_hit(self, client):
        client.post("/v1/ask", json={"query": "repeat me", "agent_type": "react"})
        data = client.post(
            "/v1/ask", json={"query": "repeat me", "agent_type": "react"}
        ).json()
        assert data["cached"] is True

    def test_ask_query_too_short(self, client):
        assert client.post("/v1/ask", json={"query": ""}).status_code == 422

    def test_ask_query_too_long(self, client):
        assert client.post(
            "/v1/ask", json={"query": "x" * 2001}
        ).status_code == 422

    def test_ask_invalid_agent_type(self, client):
        assert client.post(
            "/v1/ask", json={"query": "test", "agent_type": "nope"},
        ).status_code == 422


# ── Models ────────────────────────────────────────────────────────────────────

class TestModelsEndpoint:
    def test_list_models(self, client):
        data = client.get("/v1/models").json()
        assert "openai" in data
        assert "anthropic" in data
        assert len(data["openai"]) > 0


# ── Middleware contracts ──────────────────────────────────────────────────────

class TestMiddleware:
    def test_request_id_in_response_headers(self, client):
        resp = client.post(
            "/v1/ask", json={"query": "rid test"},
            headers={"X-Request-ID": "my-custom-id"},
        )
        assert resp.headers["X-Request-ID"] == "my-custom-id"

    def test_request_id_generated_when_absent(self, client):
        resp = client.post("/v1/ask", json={"query": "rid gen"})
        assert resp.headers.get("X-Request-ID")  # non-empty

    def test_security_headers_present(self, client):
        resp = client.get("/v1/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") is not None

    def test_health_not_rate_limited(self, client):
        """Monitoring paths bypass the limiter — 30 rapid probes OK."""
        statuses = {client.get("/v1/healthz").status_code for _ in range(30)}
        assert statuses == {200}
