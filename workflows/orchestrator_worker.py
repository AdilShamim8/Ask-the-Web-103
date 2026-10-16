"""
Orchestrator-Worker Workflow — the pattern, isolated as a workflow.

agents/orchestrator.py implements this pattern as an AGENT (LLM-decided
decomposition). This module implements it as a WORKFLOW: deterministic
fan-out/fan-in that takes the worker function as a parameter. Use it when
the partitioning is known (scrape N urls, answer M sub-questions produced
by ANY planner) and you want the guarantees without an LLM in the loop:

Guarantees:
1. WORKER ISOLATION — one worker crashing must not kill its siblings
   (FM-13). Failures return a structured error placeholder in order.
2. SHARED BUDGET — all workers draw from the parent request's budget;
   fan-out multiplies cost, so it must not multiply the ceiling (ADR-005).
3. BOUNDED CONCURRENCY — semaphore, not unbounded gather.
4. PARTIAL RESULTS — the orchestrator synthesizes from whatever came
   back; N-1 of N workers failing yields a degraded answer, not a 500.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TypeVar

import structlog

from core.budgets import BudgetManager

logger = structlog.get_logger(__name__)

T = TypeVar("T")
WorkerFn = Callable[[Any, int], Awaitable[str]]  # (item, index) -> result


@dataclass
class FanOutReport:
    """Telemetry for one orchestrator-worker run."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    elapsed_s: float = 0.0
    failures: list[str] = field(default_factory=list)

    @property
    def all_failed(self) -> bool:
        return self.total > 0 and self.succeeded == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "elapsed_s": round(self.elapsed_s, 2),
        }


class OrchestratorWorker:
    """
    Deterministic orchestrator-worker workflow.

        orchestrator.run(
            items=["url1", "url2", "url3"],
            worker=lambda item, i: my_async_fn(item),
        ) → (results_in_order, report)

    ``worker`` receives (item, index) and returns a string (workers at
    this layer are text producers; richer types live in the agent layer).
    """

    def __init__(
        self,
        *,
        max_workers: int = 4,
        worker_timeout_s: float = 20.0,
        budget: BudgetManager | None = None,
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_workers)
        self._timeout = worker_timeout_s
        self._budget = budget

    async def run(
        self,
        items: list[Any],
        worker: WorkerFn,
    ) -> tuple[list[str], FanOutReport]:
        report = FanOutReport(total=len(items))
        start = time.perf_counter()

        if not items:
            return [], report

        async def _one(index: int, item: Any) -> str:
            async with self._semaphore:
                if self._budget is not None:
                    try:
                        self._budget.consume_step()
                    except Exception:
                        return "__ERROR__ budget exhausted before worker start"
                try:
                    return await asyncio.wait_for(
                        worker(item, index), timeout=self._timeout
                    )
                except asyncio.TimeoutError:
                    report.failures.append(f"worker {index}: timeout")
                    return f"__ERROR__ worker {index} timed out"
                except Exception as exc:
                    report.failures.append(
                        f"worker {index}: {type(exc).__name__}: {str(exc)[:120]}"
                    )
                    return f"__ERROR__ worker {index}: {type(exc).__name__}"

        results = list(await asyncio.gather(*[_one(i, it) for i, it in enumerate(items)]))

        report.elapsed_s = time.perf_counter() - start
        for r in results:
            if r.startswith("__ERROR__"):
                report.failed += 1
            else:
                report.succeeded += 1

        log = logger.bind(total=report.total, ok=report.succeeded,
                          failed=report.failed)
        if report.all_failed:
            log.error("orchestrator_worker.all_failed")
        elif report.failed:
            log.warning("orchestrator_worker.partial_failure",
                        failures=report.failures[:5])
        else:
            log.info("orchestrator_worker.complete")

        return results, report

    @staticmethod
    def synthesize(
        query: str,
        results: list[str],
        report: FanOutReport,
    ) -> dict[str, Any]:
        """
        Non-LLM synthesis fallback: when workers partially failed, stitch
        what we have and mark degradation. The agent layer may replace
        this with an LLM synthesis pass; this guarantees SOMETHING
        structured comes back even in the worst case.
        """
        good = [r for r in results if not r.startswith("__ERROR__")]
        return {
            "query": query,
            "sections": good,
            "degraded": report.failed > 0,
            "degradation_reasons": report.failures[:5],
            "fan_out": report.to_dict(),
        }
