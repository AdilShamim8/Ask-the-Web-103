# ADR-005: Budgets and backpressure as first-class core objects

**Status:** Accepted · **Date:** 2026-10-16

## Context

Every reasoning strategy in this repo contains a loop: ReACT iterates,
Reflexion re-critiques, ReWOO executes plans, tree search branches. In a
teaching context `max_iterations=10` is a reasonable guard. In production,
the guard is inadequate in four independent ways:

1. **Token cost** — 10 iterations of tree search can each fan out 3 more
   branches: 30+ LLM calls, ~$1+ per hostile query, and an attacker doesn't
   need to be clever, just patient (FM-07).
2. **Tool spend** — search APIs bill per call; scrapes cost egress.
3. **Wall-clock** — a user will not wait 90s; the loop must know that.
4. **Concurrency** — orchestrator workers × in-flight requests multiply
   everything above.

## Decision

Every request creates a `BudgetManager` (`core/budgets.py`) that is
threaded through the agent/workflow/tool stack. Before every billable
action, the actor calls `budget.consume_*()`; exhaustion raises
`BudgetExceededError` which the API layer translates to a clean 422 with a
best-effort partial answer.

Budgets compose four dimensions:

```python
BudgetManager(
    max_input_tokens=...,    # prompt-side spend
    max_output_tokens=...,   # completion-side spend
    max_tool_calls=...,      # external actions
    max_steps=...,           # loop iterations (any strategy)
    deadline_s=...,          # wall-clock, from request start
)
```

Backpressure rules layered on top:

1. Providers and remote A2A agents sit behind circuit breakers — when
   downstream is unhealthy, fail fast instead of queueing.
2. Tool executor runs bounded-parallel (semaphore), never unbounded
   `gather`.
3. When budget-exceeded rate crosses 2% of queries, the router biases
   toward cheap strategies (admission control, FM-03/FM-07).

## Alternatives considered

- **Post-hoc cost reporting only:** rejected — you learn about the runaway
  from the invoice, not from the request.
- **Global rate limiting only:** rejected — limits protect the fleet, not
  the individual request; a single query can be pathological while the
  fleet looks healthy.
- **Per-strategy hardcoded caps:** rejected — the same four dimensions
  apply everywhere; centralizing them makes tuning one config change and
  makes auditing one grep.

## Consequences

- Every new loop/agent MUST call the budget API (PR checklist item).
- Budget telemetry (`budget_exceeded_total`, per-request USD histogram)
  becomes a capacity-planning input, closing the loop with
  `capacity-planning.md`.
- Tests simulate hostile inputs (infinite-tool-call models) and assert the
  request terminates bounded — the regression suite for FM-06.
