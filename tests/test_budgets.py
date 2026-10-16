"""
Budget manager tests — regression suite for FMEA FM-06/FM-07 (ADR-005).

The hostile scenario every test here encodes: a model (or attacker via
prompt) that tries to consume unbounded tokens, tools, steps, or time.
The budget manager must terminate the request deterministically.
"""

from __future__ import annotations

import time

import pytest

from core.budgets import BudgetConfig, BudgetManager, BudgetSnapshot
from core.exceptions import BudgetExceededError


def strict_budget(**overrides) -> BudgetManager:
    params = dict(
        max_input_tokens=100,
        max_output_tokens=100,
        max_tool_calls=3,
        max_steps=5,
        deadline_s=10.0,
    )
    params.update(overrides)
    return BudgetManager(BudgetConfig(**params))


class TestTokenBudgets:
    def test_consume_within_limit(self) -> None:
        budget = strict_budget()
        budget.consume_tokens(input_tokens=50, output_tokens=10)
        assert budget.input_tokens == 50
        assert budget.output_tokens == 10

    def test_input_exhaustion_raises(self) -> None:
        budget = strict_budget()
        with pytest.raises(BudgetExceededError) as exc_info:
            budget.consume_tokens(input_tokens=150, output_tokens=10)
        assert exc_info.value.dimension == "input_tokens"

    def test_output_exhaustion_raises(self) -> None:
        budget = strict_budget()
        with pytest.raises(BudgetExceededError) as exc_info:
            budget.consume_tokens(input_tokens=10, output_tokens=150)
        assert exc_info.value.dimension == "output_tokens"

    def test_error_payload_is_structured(self) -> None:
        budget = strict_budget()
        try:
            budget.consume_tokens(input_tokens=999, output_tokens=1)
            raise AssertionError("should have raised")
        except BudgetExceededError as exc:
            payload = exc.to_dict()
            assert payload["error"] == "budget_exceeded"
            assert payload["context"]["dimension"] == "input_tokens"
            assert payload["context"]["limit"] == 100

    def test_reserve_output_precheck(self) -> None:
        budget = strict_budget()
        budget.consume_tokens(input_tokens=10, output_tokens=90)
        with pytest.raises(BudgetExceededError):
            budget.reserve_output(20)  # 90 + 20 > 100


class TestToolAndStepBudgets:
    def test_tool_call_budget(self) -> None:
        budget = strict_budget()
        for _ in range(3):
            budget.consume_tool_call()
        with pytest.raises(BudgetExceededError):
            budget.consume_tool_call()

    def test_step_budget(self) -> None:
        budget = strict_budget()
        for _ in range(5):
            budget.consume_step()
        with pytest.raises(BudgetExceededError):
            budget.consume_step()

    def test_would_exceed_is_non_raising(self) -> None:
        """Planners use the non-raising check to size their work."""
        budget = strict_budget()
        assert not budget.would_exceed(input_tokens=50)
        assert budget.would_exceed(input_tokens=150)


class TestDeadlineBudget:
    def test_deadline_not_yet_reached(self) -> None:
        budget = strict_budget(deadline_s=10.0)
        budget.check_deadline()  # should not raise

    def test_deadline_exhaustion_raises(self) -> None:
        budget = strict_budget(deadline_s=0.01)
        time.sleep(0.02)
        with pytest.raises(BudgetExceededError) as exc_info:
            budget.check_deadline()
        assert exc_info.value.dimension == "deadline_s"

    def test_time_remaining(self) -> None:
        budget = strict_budget(deadline_s=10.0)
        assert 9.0 < budget.time_remaining_s() <= 10.0


class TestIntrospection:
    def test_snapshot_shape(self) -> None:
        budget = strict_budget()
        budget.consume_tokens(input_tokens=10, output_tokens=5)
        budget.consume_tool_call()
        budget.consume_step()

        snapshot: BudgetSnapshot = budget.snapshot()
        data = snapshot.to_dict()
        assert data["input_tokens"] == 10
        assert data["output_tokens"] == 5
        assert data["tool_calls"] == 1
        assert data["steps"] == 1
        assert "elapsed_s" in data


class TestRealisticHostileScenario:
    def test_runaway_agent_terminates(self) -> None:
        """
        Simulates a hostile/broken model that wants to loop forever
        calling tools. The budget must cap total damage deterministically.
        """
        budget = strict_budget(max_tool_calls=25, max_steps=12)
        tool_calls = 0
        steps = 0
        with pytest.raises(BudgetExceededError):
            while True:
                budget.consume_step()
                steps += 1
                budget.consume_tool_call()
                tool_calls += 1
        assert steps <= 12
        assert tool_calls <= 12  # step budget fires first in this pattern
