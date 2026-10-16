"""
A2A Server — exposes this agent's capabilities to remote agents.

Replaces the course-version in-memory dict store, which lost every task
on restart and grew unboundedly (FMEA FM-12). The production store:

* Redis-backed (survives worker recycling; shared across pods) with an
  in-process fallback so the feature works in dev without Redis.
* TTL-scoped tasks — abandoned tasks age out; nothing leaks.
* Result size caps — a remote agent can't stuff 50MB into our memory.
* Handler exceptions become FAILED results, never 500s to the caller.

Endpoints:
    GET  /a2a/.well-known/agent.json → AgentCard
    POST /a2a/tasks                  → submit task (returns task_id)
    GET  /a2a/tasks/{task_id}        → poll status/result
"""

from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException

from agents.a2a import AgentCard, A2ATask, A2ATaskResult, TaskStatus

logger = structlog.get_logger(__name__)

Handler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

_TASK_TTL_S = 30 * 60      # completed tasks age out after 30 min
_MAX_RESULT_BYTES = 100_000  # 100 KB result cap


class A2ATaskStore:
    """
    Task store: Redis when available, in-memory fallback otherwise.

    Fallback semantics are documented, not accidental: without Redis we
    lose cross-pod visibility and durability, but the protocol keeps
    working for single-pod dev — availability over completeness (FM-05
    fail-open philosophy).
    """

    def __init__(self, redis: Any | None = None, prefix: str = "a2a:task:") -> None:
        self._redis = redis
        self._local: dict[str, str] = {}
        self._prefix = prefix

    async def set(self, task_id: str, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload)[:_MAX_RESULT_BYTES]
        if self._redis is not None:
            await self._redis.set(f"{self._prefix}{task_id}", raw, ex=_TASK_TTL_S)
        else:
            self._local[task_id] = raw
            # crude local TTL: drop old entries when the map grows
            if len(self._local) > 10_000:
                self._local.clear()

    async def get(self, task_id: str) -> dict[str, Any] | None:
        if self._redis is not None:
            raw = await self._redis.get(f"{self._prefix}{task_id}")
        else:
            raw = self._local.get(task_id)
        if raw is None:
            return None
        return json.loads(raw)


def create_a2a_server(
    agent_card: AgentCard,
    handler: Handler,
    store: A2ATaskStore | None = None,
) -> APIRouter:
    """
    Factory: A2A-compliant FastAPI routes for any agent.

    handler(capability, input_data) → output_dict
    """
    router = APIRouter(prefix="/a2a", tags=["A2A"])
    task_store = store or A2ATaskStore()

    @router.get("/.well-known/agent.json", response_model=AgentCard)
    async def get_agent_card() -> AgentCard:
        return agent_card

    @router.post("/tasks", response_model=A2ATaskResult, status_code=202)
    async def submit_task(
        task: A2ATask, background: BackgroundTasks
    ) -> A2ATaskResult:
        # Reject work the caller can't wait for (deadlines flow through ADR-005).
        if task.deadline_s is not None and task.deadline_s <= 0:
            raise HTTPException(
                status_code=400,
                detail="task deadline_s must be positive",
            )

        result = A2ATaskResult(task_id=task.task_id, status=TaskStatus.SUBMITTED)
        await task_store.set(task.task_id, result.model_dump())

        async def _run() -> None:
            start = time.perf_counter()
            try:
                output = await handler(task.capability, task.input)
                await task_store.set(task.task_id, A2ATaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.COMPLETED,
                    output=output,
                    elapsed_s=round(time.perf_counter() - start, 2),
                ).model_dump())
            except Exception as exc:
                logger.warning(
                    "a2a_server.task_failed",
                    task_id=task.task_id,
                    error=str(exc)[:200],
                )
                await task_store.set(task.task_id, A2ATaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    error=str(exc)[:512],
                    elapsed_s=round(time.perf_counter() - start, 2),
                ).model_dump())

        background.add_task(_run)
        return result

    @router.get("/tasks/{task_id}", response_model=A2ATaskResult)
    async def get_task(task_id: str) -> A2ATaskResult:
        data = await task_store.get(task_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Task not found or expired")
        return A2ATaskResult(**data)

    return router
