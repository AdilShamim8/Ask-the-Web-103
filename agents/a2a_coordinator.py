"""
Multi-Agent Coordinator — capability routing across remote A2A agents.

The coordinator maps capability names to A2AClient instances and
delegates sub-tasks to the right specialist. Design decisions (ADR-004):

* Health-aware routing: every remote agent sits behind its own circuit
  breaker (in A2AClient). A dead specialist raises A2AError fast instead
  of stalling the orchestrator — the caller can retry with a fallback
  capability or degrade (FM-12/FM-13).
* ``delegate_parallel`` fans out with exception isolation per task: one
  remote agent failing returns its error in-place; siblings complete.
* Deadline propagation: caller wall-clock budget flows into every A2A
  call — fan-out never exceeds the request envelope (ADR-005).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from agents.a2a import A2AClient, A2ATaskResult, TaskStatus
from core.exceptions import A2AError

logger = structlog.get_logger(__name__)


class MultiAgentCoordinator:
    """
    Coordinates specialized agents via the A2A protocol.

    Registry maps capability names to A2AClient instances; the
    coordinator routes sub-tasks to the appropriate specialist.
    """

    def __init__(self) -> None:
        self._agents: dict[str, A2AClient] = {}

    def register_agent(self, capability: str, client: A2AClient) -> MultiAgentCoordinator:
        self._agents[capability] = client
        logger.info(
            "multi_agent.registered",
            capability=capability,
            agent=client.card.name,
        )
        return self

    @property
    def capabilities(self) -> list[str]:
        return sorted(self._agents.keys())

    async def delegate(
        self,
        capability: str,
        input_data: dict[str, Any],
        *,
        deadline_s: float | None = None,
    ) -> dict[str, Any]:
        """Delegate a task to the specialist for ``capability``."""
        if capability not in self._agents:
            raise A2AError(
                f"No agent registered for capability: '{capability}'. "
                f"Available: {self.capabilities}",
                context={"capability": capability},
            )

        client = self._agents[capability]
        result: A2ATaskResult = await client.call(
            capability, input_data, deadline_s=deadline_s
        )

        if result.status == TaskStatus.FAILED:
            raise A2AError(
                f"Agent '{client.card.name}' failed: {result.error}",
                context={"agent": client.card.agent_id, "task_id": result.task_id},
            )

        return result.output

    async def delegate_parallel(
        self,
        tasks: list[tuple[str, dict[str, Any]]],
        *,
        deadline_s: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Delegate independent tasks in parallel, isolated per task.

        Returns results in order; a failed delegation yields
        {"error": ...} in its slot — never an exception that kills the
        batch (FM-13). Callers inspect for "error" keys.
        """
        if deadline_s is not None:
            start = time.monotonic()

        async def _one(capability: str, data: dict[str, Any]) -> dict[str, Any]:
            try:
                remaining = None
                if deadline_s is not None:
                    remaining = deadline_s - (time.monotonic() - start)
                    if remaining <= 0:
                        return {"error": f"deadline exhausted before '{capability}'"}
                return await self.delegate(
                    capability, data, deadline_s=remaining
                )
            except A2AError as exc:
                logger.warning(
                    "multi_agent.delegate_failed",
                    capability=capability,
                    error=str(exc)[:200],
                )
                return {"error": str(exc)}

        coros = [_one(cap, inp) for cap, inp in tasks]
        return list(await asyncio.gather(*coros))
