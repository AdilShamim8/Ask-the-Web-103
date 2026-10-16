# Agent & Pattern Catalog

**Last updated:** 2026-10-16

The course-to-code map: every concept from the curriculum, where it
lives in this repo, and the production behavior layered on top of it.

## 1. Agents Overview

| Concept | Where | Production layer |
| ------- | ----- | ---------------- |
| LLMs vs. agents vs. agentic systems | `Tutorial-103.md` ch. 2 · `agents/base_agent.py` | `BaseAgent` = the "agent" contract: state, budgets, usage, degradation |
| Agency levels (workflows → multi-step → multi-agent) | Tutorial ch. 2.3 | Explicit in module split: `workflows/` (deterministic) → `agents/` (autonomous) → A2A (federated) |

## 2. Workflows (deterministic composition)

| Pattern | Module | Production behavior |
| ------- | ------ | ------------------- |
| Prompt chaining | `workflows/prompt_chaining.py` | Budget-gated steps, fast model tier, early exit, strict key errors |
| Routing | `workflows/routing.py` | Free rule-based fast path; LLM classification cached 10 min per normalized query |
| Parallelization — sectioning | `workflows/parallelization.py` | Bounded semaphore, per-item timeout, exception isolation |
| Parallelization — voting | `workflows/parallelization.py` | Capped votes, deterministic tie-break, agreement telemetry |
| Reflection | `workflows/reflection.py` | Hard round cap, budget steps, no private-attribute access |
| Orchestrator-worker | `workflows/orchestrator_worker.py` | Worker isolation, shared budget, partial degradation markers |

## 3. Tools

| Concept | Module | Production behavior |
| ------- | ------ | ------------------- |
| Tool calling | `tools/base_tool.py` + `tools/tool_executor.py` | Schema-declared tools; LLM args validated before execution |
| Tool formatting | `tools/base_tool.py` | OpenAI + Anthropic wire formats from one `ToolDefinition` |
| Tool execution | `tools/tool_executor.py` | Timeout, budget hook, SSRF re-check, truncation, metrics — centrally enforced |
| Registry | `tools/tool_registry.py` | Freeze-after-startup, health checks, namespacing |
| Web tools | `tools/web_search.py` · `tools/web_scraper.py` | Provider fallback chains; SSRF guard, byte caps, content-type allowlist, off-loop parsing |
| MCP | `tools/mcp_client.py` · `tools/mcp_server.py` | Session reuse, TTL discovery cache, breakers; we also SERVE tools over MCP with all guards (ADR-004) |

## 4. Multi-Step Agents (autonomous reasoning)

| Strategy | Module | Termination & cost control |
| -------- | ------ | -------------------------- |
| Planning autonomy | `agents/planner.py` | DAG validation (cycles, unknown deps); invalid plans route to safest agent |
| ReACT | `agents/react_agent.py` | Per-iteration deadline/step/token gates; degrade with partial answer |
| Reflexion | `agents/reflexion_agent.py` | Reflections capped at 3; budget shared with inner ReACT |
| ReWOO | `agents/rewoo_agent.py` | Plan clamped to budget; evidence-escaped JSON substitution; failed steps skipped |
| Tree search | `agents/tree_search_agent.py` | Hard envelope (branch≤3, beam≤3, depth≤4); beam shrinks as budget drains |

## 5. Multi-Agent Systems

| Concept | Module | Production behavior |
| ------- | ------ | ------------------- |
| Challenges (isolation, partial failure) | `agents/orchestrator.py` | `gather(return_exceptions=True)` + per-worker placeholders |
| Use-cases (specialization, fan-out) | `agents/a2a_coordinator.py` | Capability registry, isolated parallel delegation |
| A2A protocol | `agents/a2a.py` · `agents/a2a_server.py` · `api/a2a_routes.py` | AgentCards, task lifecycle, Redis-backed store with TTL/caps, deadline propagation, breakers per remote agent |

## 6. Agent Evaluation

| Concept | Module | Production behavior |
| ------- | ------ | ------------------- |
| Metrics | `evaluation/metrics.py` | Citation coverage AND precision (fabrication rate), structure, length |
| LLM evaluator | `evaluation/evaluator.py` | Multi-dimension rubric on the fast model tier |
| Benchmarks | `evaluation/benchmarks.py` | Golden dataset, category scoring, CI gate (exit code) |
| Golden set | `evaluation/datasets/golden_v1.json` | 10 cases across 6 categories incl. adversarial-vague |

## 7. Cross-cutting production concerns

| Concern | Module |
| ------- | ------ |
| Budgets (ADR-005) | `core/budgets.py` |
| Resilience (retry, breaker, token bucket) | `core/resilience.py` |
| Usage & cost | `core/usage_tracker.py` |
| Observability | `core/observability.py` · `configs/prometheus.yml` |
| Cache (ADR-003) | `api/cache.py` |
| Rate limiting & security headers | `api/middleware.py` |
| SSE streaming | `api/streaming.py` |
| DI & wiring | `api/dependencies.py` · `api/main.py` |
