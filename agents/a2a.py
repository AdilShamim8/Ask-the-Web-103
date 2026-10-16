from __future__ import annotations

"""
A2A — Agent-to-Agent Communication Protocol

Implements Google's Agent-to-Agent (A2A) protocol pattern:
https://google.github.io/A2A/

Core concepts:
    AgentCard     — Declares what an agent can do (like an API schema)
    Task          — A unit of work sent from one agent to another
    A2AServer     — Exposes an agent as an HTTP endpoint
    A2AClient     — Calls remote agents as if they were local tools

This enables true multi-agent systems where specialized agents
collaborate to solve complex problems.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
import structlog
from pydantic import BaseModel

from core.message_types import AgentState

logger = structlog.get_logger(__name__)


# ── Protocol Types ────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    SUBMITTED  = "submitted"
    WORKING    = "working"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


class AgentCapability(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}


class AgentCard(BaseModel):
    """
    Describes an agent's identity and capabilities.
    Published at /.well-known/agent.json per A2A spec.
    """
    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    url: str
    capabilities: list[AgentCapability] = []
    auth_required: bool = False


class A2ATask(BaseModel):
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    capability: str
    input: dict[str, Any]
    caller_agent_id: str = ""
    metadata: dict[str, Any] = {}


class A2ATaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    output: dict[str, Any] = {}
    error: str | None = None
    elapsed_s: float = 0.0


# ── A2A Client ────────────────────────────────────────────────────────────────

class A2AClient:
    """
    Calls a remote agent via the A2A protocol.
    Can be used as a tool by the orchestrator.
    """

    def __init__(
        self,
        agent_card: AgentCard,
        timeout: float = 120.0,
        api_key: str = "",
    ) -> None:
        self._card = agent_card
        self._timeout = timeout
        self._api_key = api_key

    async def call(
        self,
        capability: str,
        input_data: dict[str, Any],
        poll_interval: float = 1.0,
    ) -> A2ATaskResult:
        """
        Submit a task to the remote agent and poll until completion.
        Implements the async task pattern from the A2A spec.
        """
        log = logger.bind(
            remote_agent=self._card.name,
            capability=capability,
        )
        log.info("a2a.task.submit")

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        task = A2ATask(
            capability=capability,
            input=input_data,
        )

        async with httpx.AsyncClient(
            timeout=self._timeout, headers=headers
        ) as client:
            # Submit task
            resp = await client.post(
                f"{self._card.url}/a2a/tasks",
                json=task.model_dump(),
            )
            resp.raise_for_status()
            submitted = resp.json()
            task_id = submitted["task_id"]

            # Poll for completion
            start = time.perf_counter()
            while True:
                await asyncio.sleep(poll_interval)
                status_resp = await client.get(
                    f"{self._card.url}/a2a/tasks/{task_id}"
                )
                status_resp.raise_for_status()
                result_data = status_resp.json()
                status = TaskStatus(result_data["status"])

                if status == TaskStatus.COMPLETED:
                    log.info(
                        "a2a.task.completed",
                        elapsed_s=round(time.perf_counter() - start, 2),
                    )
                    return A2ATaskResult(**result_data)

                if status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                    log.error("a2a.task.failed", status=status)
                    return A2ATaskResult(**result_data)

                if time.perf_counter() - start > self._timeout:
                    return A2ATaskResult(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        error="A2A task timed out",
                    )

    async def get_agent_card(self) -> AgentCard:
        """Fetch the remote agent's capability card."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self._card.url}/.well-known/agent.json"
            )
            resp.raise_for_status()
            return AgentCard(**resp.json())


# ── A2A Server Routes (FastAPI) ───────────────────────────────────────────────

from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Callable, Awaitable

a2a_router = APIRouter(prefix="/a2a", tags=["A2A"])

# In-memory task store (use Redis in production)
_task_store: dict[str, A2ATaskResult] = {}


def create_a2a_server(
    agent_card: AgentCard,
    handler: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
) -> APIRouter:
    """
    Factory: creates A2A-compliant FastAPI routes for any agent.

    handler(capability, input_data) → output_dict
    """
    router = APIRouter(prefix="/a2a", tags=["A2A"])

    @router.get("/.well-known/agent.json", response_model=AgentCard)
    async def get_agent_card() -> AgentCard:
        return agent_card

    @router.post("/tasks", response_model=A2ATaskResult)
    async def submit_task(
        task: A2ATask,
        background: BackgroundTasks,
    ) -> A2ATaskResult:
        result = A2ATaskResult(
            task_id=task.task_id,
            status=TaskStatus.SUBMITTED,
        )
        _task_store[task.task_id] = result

        async def _run() -> None:
            _task_store[task.task_id] = A2ATaskResult(
                task_id=task.task_id,
                status=TaskStatus.WORKING,
            )
            start = time.perf_counter()
            try:
                output = await handler(task.capability, task.input)
                _task_store[task.task_id] = A2ATaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.COMPLETED,
                    output=output,
                    elapsed_s=round(time.perf_counter() - start, 2),
                )
            except Exception as exc:
                _task_store[task.task_id] = A2ATaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    error=str(exc),
                    elapsed_s=round(time.perf_counter() - start, 2),
                )

        background.add_task(_run)
        return result

    @router.get("/tasks/{task_id}", response_model=A2ATaskResult)
    async def get_task(task_id: str) -> A2ATaskResult:
        if task_id not in _task_store:
            raise HTTPException(status_code=404, detail="Task not found")
        return _task_store[task_id]

    return router


# ── Multi-Agent System using A2A ──────────────────────────────────────────────

class MultiAgentCoordinator:
    """
    Coordinates multiple specialized agents via A2A protocol.

    Registry maps capability names to A2AClient instances.
    The coordinator routes sub-tasks to the appropriate specialist agent.
    """

    def __init__(self) -> None:
        self._agents: dict[str, A2AClient] = {}

    def register_agent(
        self, capability: str, client: A2AClient
    ) -> "MultiAgentCoordinator":
        self._agents[capability] = client
        logger.info(
            "multi_agent.registered",
            capability=capability,
            agent=client._card.name,
        )
        return self

    async def delegate(
        self,
        capability: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Delegate a task to the agent best suited for the capability."""
        if capability not in self._agents:
            raise ValueError(
                f"No agent registered for capability: '{capability}'. "
                f"Available: {list(self._agents.keys())}"
            )

        client = self._agents[capability]
        result = await client.call(capability=capability, input_data=input_data)

        if result.status == TaskStatus.FAILED:
            raise RuntimeError(
                f"Agent '{client._card.name}' failed: {result.error}"
            )

        return result.output

    async def delegate_parallel(
        self,
        tasks: list[tuple[str, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Delegate multiple independent tasks in parallel."""
        coros = [self.delegate(cap, inp) for cap, inp in tasks]
        return list(await asyncio.gather(*coros))