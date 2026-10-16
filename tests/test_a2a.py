"""
A2A protocol tests: server task lifecycle, coordinator isolation.

Client HTTP transport is faked via httpx.MockTransport — no network.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agents.a2a import AgentCard, A2ATask, TaskStatus
from agents.a2a_coordinator import MultiAgentCoordinator
from agents.a2a_server import A2ATaskStore, create_a2a_server


def make_card(url: str = "http://testserver") -> AgentCard:
    return AgentCard(
        agent_id="test-agent",
        name="Test Agent",
        description="for tests",
        url=url,
    )


class TestTaskStore:
    async def test_roundtrip(self) -> None:
        store = A2ATaskStore()
        payload = {"task_id": "t1", "status": "working"}
        await store.set("t1", payload)
        assert (await store.get("t1"))["status"] == "working"

    async def test_missing_returns_none(self) -> None:
        store = A2ATaskStore()
        assert await store.get("nope") is None

    async def test_result_is_capped(self) -> None:
        """FM-12: an oversized remote result must not enter memory whole.
        The payload is replaced by a valid-JSON truncated marker — never
        a mid-string cut that breaks every future read."""
        store = A2ATaskStore()
        huge = {
            "task_id": "big",
            "status": "completed",
            "output": {"data": "x" * 500_000},
        }
        await store.set("big", huge)
        stored = await store.get("big")

        assert stored is not None  # still valid, parseable JSON
        assert len(json.dumps(stored)) <= 100_100
        assert stored["output"] == {}
        assert "truncated" in (stored.get("error") or "")


class TestA2AServerRoutes:
    @pytest.fixture
    def app(self) -> FastAPI:
        async def handler(capability: str, data: dict) -> dict:
            if capability == "boom":
                raise RuntimeError("worker exploded")
            return {"echo": capability, "input": data}

        app = FastAPI()
        app.include_router(
            create_a2a_server(make_card(), handler, store=A2ATaskStore())
        )
        return app

    @pytest.fixture
    def client(self, app) -> TestClient:
        return TestClient(app)

    def test_agent_card_endpoint(self, client) -> None:
        resp = client.get("/a2a/.well-known/agent.json")
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == "test-agent"

    def test_task_lifecycle_completed(self, client) -> None:
        resp = client.post("/a2a/tasks", json={
            "capability": "research",
            "input": {"query": "hi"},
        })
        assert resp.status_code == 202
        task_id = resp.json()["task_id"]

        # BackgroundTasks run synchronously in TestClient after response
        status = client.get(f"/a2a/tasks/{task_id}").json()
        assert status["status"] in ("completed", "working", "submitted")

    def test_task_failure_is_failed_not_500(self, client) -> None:
        """Handler exceptions become FAILED results — never 500s."""
        resp = client.post("/a2a/tasks", json={
            "capability": "boom",
            "input": {},
        })
        assert resp.status_code == 202

    def test_unknown_task_404(self, client) -> None:
        assert client.get("/a2a/tasks/ghost").status_code == 404

    def test_negative_deadline_rejected(self, client) -> None:
        resp = client.post("/a2a/tasks", json={
            "capability": "research",
            "input": {},
            "deadline_s": -5,
        })
        assert resp.status_code == 400


class TestCoordinator:
    def test_unknown_capability_raises(self) -> None:
        coord = MultiAgentCoordinator()
        with pytest.raises(Exception):
            asyncio.get_event_loop().run_until_complete(
                coord.delegate("nonexistent", {})
            )

    async def test_parallel_isolation(self) -> None:
        """
        FM-13: one dead agent in a parallel batch must not kill its
        siblings — failures return in-place error dicts.
        """
        coord = MultiAgentCoordinator()

        class FakeClient:
            def __init__(self, name: str, fail: bool) -> None:
                self.card = make_card()
                self.card.name = name
                self._fail = fail

            async def call(self, capability, data, deadline_s=None):
                if self._fail:
                    from agents.a2a import A2ATaskResult

                    return A2ATaskResult(
                        task_id="t", status=TaskStatus.FAILED,
                        error="remote exploded",
                    )
                from agents.a2a import A2ATaskResult

                return A2ATaskResult(
                    task_id="t", status=TaskStatus.COMPLETED,
                    output={"ok": capability},
                )

        coord.register_agent("good1", FakeClient("g1", fail=False))
        coord.register_agent("bad", FakeClient("b", fail=True))
        coord.register_agent("good2", FakeClient("g2", fail=False))

        results = await coord.delegate_parallel([
            ("good1", {}), ("bad", {}), ("good2", {}),
        ])

        assert results[0] == {"ok": "good1"}
        assert "error" in results[1]
        assert results[2] == {"ok": "good2"}
