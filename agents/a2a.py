"""
A2A — Agent-to-Agent protocol: types + client.

Protocol: https://google.github.io/A2A/

Core concepts:
    AgentCard     — declares what an agent can do (like an API schema)
    A2ATask       — a unit of work sent from one agent to another
    A2ATaskResult — lifecycle-tracked outcome

This module is the CLIENT side (calling remote agents). The SERVER side
(exposing this agent over A2A) lives in a2a_server.py; the multi-agent
coordinator lives in a2a_coordinator.py.

Production hardening:
* Per-remote-agent circuit breaker — a dead specialist fails fast and
  stops consuming request time (FM-01/FM-12).
* Polling is bounded: max poll duration, exponential poll interval with
  jitter (no 1s-fixed-interval hammering of a busy agent).
* The task submission includes a deadline derived from the caller's
  remaining wall-clock budget (ADR-005) — remote agents can't eat time
  the request doesn't have.
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from core.exceptions import A2AError, ProviderUnavailableError
from core.resilience import BreakerRegistry
from tools.http_client import get_http_client

logger = structlog.get_logger(__name__)

_breakers = BreakerRegistry()


# ── Protocol Types ────────────────────────────────────────────────────────────


class TaskStatus(StrEnum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentCapability(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class AgentCard(BaseModel):
    """Describes an agent's identity and capabilities (/.well-known/agent.json)."""

    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    url: str
    capabilities: list[AgentCapability] = Field(default_factory=list)
    auth_required: bool = False


class A2ATask(BaseModel):
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    capability: str
    input: dict[str, Any] = Field(default_factory=dict)
    caller_agent_id: str = ""
    deadline_s: float | None = None   # caller's remaining wall-clock budget
    metadata: dict[str, Any] = Field(default_factory=dict)


class A2ATaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    elapsed_s: float = 0.0


# ── A2A Client ────────────────────────────────────────────────────────────────


class A2AClient:
    """Calls a remote agent via the A2A protocol, under breaker protection."""

    def __init__(
        self,
        agent_card: AgentCard,
        timeout: float = 120.0,
        api_key: str = "",
    ) -> None:
        self._card = agent_card
        self._timeout = timeout
        self._api_key = api_key

    @property
    def card(self) -> AgentCard:
        return self._card

    async def call(
        self,
        capability: str,
        input_data: dict[str, Any],
        *,
        deadline_s: float | None = None,
    ) -> A2ATaskResult:
        """
        Submit a task and poll until completion (async task pattern).

        ``deadline_s``: remaining caller budget. Polling stops and the
        task is treated as timed out when exceeded — remote work must fit
        inside the request's wall-clock envelope (ADR-005).
        """
        log = logger.bind(remote_agent=self._card.name, capability=capability)

        breaker = _breakers.get_or_create(f"a2a:{self._card.agent_id}")

        async def _do_call() -> A2ATaskResult:
            return await self._submit_and_poll(
                capability, input_data, deadline_s, log
            )

        try:
            return await breaker.call(_do_call)
        except ProviderUnavailableError as exc:
            raise A2AError(
                f"remote agent '{self._card.name}' unavailable: {exc}",
                context={"agent": self._card.agent_id},
            ) from exc
        except Exception as exc:
            raise A2AError(
                f"A2A call to '{self._card.name}' failed: {exc}",
                context={"agent": self._card.agent_id},
            ) from exc

    async def _submit_and_poll(
        self,
        capability: str,
        input_data: dict[str, Any],
        deadline_s: float | None,
        log: Any,
    ) -> A2ATaskResult:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        client = get_http_client()

        task = A2ATask(
            capability=capability,
            input=input_data,
            deadline_s=deadline_s,
        )

        log.info("a2a.task.submit")

        resp = await client.post(
            f"{self._card.url}/a2a/tasks",
            json=task.model_dump(),
            headers=headers,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        submitted = resp.json()
        task_id = submitted["task_id"]

        # Poll with exponential backoff + jitter (be gentle with busy agents)
        start = time.perf_counter()
        poll_interval = 0.5
        max_poll = deadline_s or self._timeout

        while True:
            await asyncio.sleep(poll_interval + random.uniform(0, 0.2))
            poll_interval = min(2.0, poll_interval * 1.5)

            elapsed = time.perf_counter() - start
            if elapsed > max_poll:
                log.warning("a2a.task.timeout", task_id=task_id, elapsed_s=elapsed)
                return A2ATaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error=f"A2A task timed out after {elapsed:.1f}s",
                )

            status_resp = await client.get(
                f"{self._card.url}/a2a/tasks/{task_id}",
                headers=headers,
                timeout=30.0,
            )
            status_resp.raise_for_status()
            result_data = status_resp.json()
            status = TaskStatus(result_data["status"])

            if status == TaskStatus.COMPLETED:
                log.info("a2a.task.completed", elapsed_s=round(elapsed, 2))
                return A2ATaskResult(**result_data)

            if status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                log.error("a2a.task.failed", status=status)
                return A2ATaskResult(**result_data)

    async def get_agent_card(self) -> AgentCard:
        """Fetch/refresh the remote agent's capability card."""
        client = get_http_client()
        resp = await client.get(
            f"{self._card.url}/.well-known/agent.json", timeout=10.0
        )
        resp.raise_for_status()
        return AgentCard(**resp.json())
