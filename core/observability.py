"""
Observability: Prometheus metrics + shared metric helpers.

RED-method metrics (Rate, Errors, Duration) for every layer, plus
domain-specific series the runbook and FMEA depend on. Every counter /
histogram here is referenced by an alert or dashboard query — no vanity
metrics.

All series are process-local; Prometheus scrapes ``/metrics`` per pod and
aggregates. That keeps the hot path allocation-free (no network hop).
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── HTTP layer (api/) ─────────────────────────────────────────────────────────

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests by route/method/status",
    ["route", "method", "status"],
)

HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["route"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

RATE_LIMITED = Counter(
    "rate_limited_total",
    "Requests rejected by the rate limiter",
    ["scope"],  # "global" | "per_user"
)

# ── LLM layer (core/llm_client.py) ───────────────────────────────────────────

LLM_CALLS = Counter(
    "llm_calls_total",
    "LLM calls by provider/model/outcome",
    ["provider", "model", "outcome"],  # outcome: ok | error | budget_blocked
)

LLM_LATENCY = Histogram(
    "llm_call_duration_seconds",
    "LLM call latency",
    ["provider"],
    buckets=(0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Token usage",
    ["provider", "direction"],  # direction: input | output
)

REQUEST_COST = Histogram(
    "request_cost_usd",
    "Estimated USD cost per request",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0),
)

LLM_PROVIDER_UP = Gauge(
    "llm_provider_up",
    "1 if last call to provider succeeded, else 0",
    ["provider"],
)

# ── Tool layer (tools/) ───────────────────────────────────────────────────────

TOOL_CALLS = Counter(
    "tool_calls_total",
    "Tool invocations by tool/outcome",
    ["tool", "outcome"],  # outcome: ok | error | timeout | ssrf_blocked | truncated
)

TOOL_LATENCY = Histogram(
    "tool_call_duration_seconds",
    "Tool call latency",
    ["tool"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0),
)

SSRF_BLOCKED = Counter(
    "ssrf_blocked_total",
    "URLs rejected by the SSRF guard",
    ["reason"],
)

# ── Cache layer (api/cache.py) ────────────────────────────────────────────────

CACHE_REQUESTS = Counter(
    "cache_requests_total",
    "Cache lookups by layer",
    ["layer", "result"],  # layer: l1|l2, result: hit|miss|stale
)

SINGLEFLIGHT = Counter(
    "singleflight_total",
    "Singleflight outcomes",
    ["outcome"],  # winner | follower | timeout | lock_error
)

# ── Agents (agents/) ─────────────────────────────────────────────────────────

AGENT_RUNS = Counter(
    "agent_runs_total",
    "Agent executions by type/outcome",
    ["agent_type", "outcome"],  # ok | error | budget_exceeded | max_iterations
)

AGENT_LATENCY = Histogram(
    "agent_run_duration_seconds",
    "End-to-end agent execution time",
    ["agent_type"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 45.0, 90.0),
)

BUDGET_EXCEEDED = Counter(
    "budget_exceeded_total",
    "Requests terminated by budget guard",
    ["dimension"],  # input_tokens | output_tokens | tool_calls | steps | deadline_s
)

# ── Circuit breakers (core/resilience.py) ────────────────────────────────────

CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Breaker state: 0=closed 1=open 2=half-open",
    ["breaker"],
)


def observe_breaker(name: str, state_value: int) -> None:
    """Publish breaker state (called on state transitions)."""
    CIRCUIT_BREAKER_STATE.labels(breaker=name).set(state_value)
