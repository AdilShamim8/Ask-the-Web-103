"""
Orchestrator-worker workflow tests — the FM-13 regression suite:
worker isolation, partial results, bounded concurrency.
"""

from __future__ import annotations

import asyncio

from core.budgets import BudgetConfig, BudgetManager
from workflows.orchestrator_worker import FanOutReport, OrchestratorWorker


class TestWorkerIsolation:
    async def test_one_failure_does_not_kill_siblings(self) -> None:
        async def worker(item: int, index: int) -> str:
            if item == 2:
                raise RuntimeError("worker 2 exploded")
            await asyncio.sleep(0.01)
            return f"result-{item}"

        ow = OrchestratorWorker(max_workers=3)
        results, report = await ow.run([1, 2, 3], worker)

        assert results[0] == "result-1"
        assert results[1].startswith("__ERROR__")
        assert results[2] == "result-3"

        assert report.total == 3
        assert report.succeeded == 2
        assert report.failed == 1
        assert not report.all_failed

    async def test_timeout_returns_error_marker(self) -> None:
        async def slow_worker(item: int, index: int) -> str:
            await asyncio.sleep(5)  # would block forever without timeout
            return "late"

        ow = OrchestratorWorker(max_workers=1, worker_timeout_s=0.05)
        results, report = await ow.run([1], slow_worker)

        assert results[0].startswith("__ERROR__")
        assert "timed out" in results[0]
        assert report.failed == 1

    async def test_all_failed_flag(self) -> None:
        async def always_fails(item, index):
            raise ValueError("no")

        ow = OrchestratorWorker()
        _, report = await ow.run([1, 2], always_fails)
        assert report.all_failed


class TestConcurrency:
    async def test_bounded_parallelism(self) -> None:
        """The semaphore must cap simultaneous workers."""
        concurrent = {"now": 0, "max": 0}

        async def worker(item: int, index: int) -> str:
            concurrent["now"] += 1
            concurrent["max"] = max(concurrent["max"], concurrent["now"])
            await asyncio.sleep(0.05)
            concurrent["now"] -= 1
            return "ok"

        ow = OrchestratorWorker(max_workers=2)
        await ow.run(list(range(10)), worker)
        assert concurrent["max"] <= 2

    async def test_empty_items(self) -> None:
        ow = OrchestratorWorker()
        results, report = await ow.run([], lambda item, i: "x")
        assert results == []
        assert report.total == 0
        assert not report.all_failed


class TestBudgetIntegration:
    async def test_shared_budget_caps_total_work(self) -> None:
        """ADR-005: fan-out multiplies cost, not the ceiling."""
        budget = BudgetManager(BudgetConfig(max_steps=3))

        async def worker(item: int, index: int) -> str:
            await asyncio.sleep(0.01)
            return "ok"

        ow = OrchestratorWorker(max_workers=4, budget=budget)
        results, report = await ow.run([1, 2, 3, 4, 5, 6], worker)

        # Steps consumed: capped at 3 — workers 4+ got budget-blocked.
        assert budget.steps <= 3
        assert report.succeeded <= 3


class TestSynthesize:
    def test_synthesize_marks_degradation(self) -> None:
        ow = OrchestratorWorker()
        report = FanOutReport(total=3, succeeded=2, failed=1,
                              failures=["worker 2: timeout"])
        out = ow.synthesize("q?", ["good1", "__ERROR__ worker 2: timeout", "good2"], report)
        assert out["degraded"] is True
        assert len(out["sections"]) == 2
        assert "worker 2: timeout" in out["degradation_reasons"]

    def test_synthesize_clean_when_all_good(self) -> None:
        ow = OrchestratorWorker()
        report = FanOutReport(total=2, succeeded=2, failed=0)
        out = ow.synthesize("q?", ["a", "b"], report)
        assert out["degraded"] is False
        assert out["sections"] == ["a", "b"]
