"""
Usage/cost tracking tests — the accounting behind capacity-planning §3.
"""

from __future__ import annotations

from core.usage_tracker import (
    DEFAULT_PRICING,
    UsageReport,
    UsageTracker,
    estimate_cost_usd,
)


class TestPricing:
    def test_known_model_priced(self) -> None:
        # gpt-4o: $2.50/1M in, $10.00/1M out
        cost = estimate_cost_usd("gpt-4o", 1_000_000, 1_000_000)
        assert abs(cost - 12.50) < 0.001

    def test_unknown_model_gets_conservative_default(self) -> None:
        """Unmapped models must NOT report $0 — silent cost is worse
        than an overestimate."""
        cost = estimate_cost_usd("mystery-model-9000", 1_000_000, 0)
        assert cost > 0

    def test_zero_tokens_zero_cost(self) -> None:
        assert estimate_cost_usd("gpt-4o", 0, 0) == 0.0


class TestUsageTracker:
    def test_record_llm_call_aggregates(self) -> None:
        tracker = UsageTracker()
        tracker.record_llm_call("openai", "gpt-4o", 1_000, 500)
        tracker.record_llm_call("openai", "gpt-4o", 2_000, 500)
        tracker.record_llm_call("anthropic", "claude-3-haiku-20240307", 100, 100)

        report: UsageReport = tracker.report
        assert report.llm_calls == 3
        assert report.input_tokens == 3_100
        assert report.output_tokens == 1_100
        assert report.total_cost_usd > 0

    def test_tool_call_counting(self) -> None:
        tracker = UsageTracker()
        tracker.record_tool_call("web_search")
        tracker.record_tool_call("web_search")
        tracker.record_tool_call("scrape_webpage")
        tracker.record_tool_call("calculator")

        assert tracker.report.tool_calls == 4
        assert tracker.report.web_searches == 2
        assert tracker.report.pages_fetched == 1

    def test_to_dict_shape(self) -> None:
        tracker = UsageTracker()
        tracker.record_llm_call("openai", "gpt-4o", 10, 10)
        data = tracker.to_dict()
        for key in ("llm_calls", "input_tokens", "output_tokens",
                    "tool_calls", "web_searches", "pages_fetched",
                    "estimated_cost_usd", "by_model"):
            assert key in data

    def test_cost_math_matches_pricing_table(self) -> None:
        tracker = UsageTracker()
        tracker.record_llm_call("openai", "gpt-4o", 1_000_000, 1_000_000)
        assert abs(tracker.report.total_cost_usd - 12.50) < 0.001

    def test_export_cost_metric_does_not_raise(self) -> None:
        tracker = UsageTracker()
        tracker.record_llm_call("openai", "gpt-4o", 100, 100)
        tracker.export_cost_metric()  # Prometheus observe — must not raise
