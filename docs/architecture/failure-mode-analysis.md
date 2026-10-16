# Failure Mode & Effects Analysis (FMEA)

**Status:** Active · **Last updated:** 2026-10-16

This is the "where does it break and why" register. Every entry lists the
trigger, blast radius, the signal that fires in monitoring, and the
mitigation that exists in code today. On-call starts here.

Severity: **S1** = user-visible outage · **S2** = degraded quality/cost ·
**S3** = operational toil / latent risk.

| ID | Failure mode | Trigger | Blast radius | Detection signal | Mitigation in code |
| -- | ------------ | ------- | ------------ | ---------------- | ------------------ |
| FM-01 | LLM provider outage / quota exhaustion | Vendor incident or rate-limit storm | All uncached answers fail | `llm_provider_up` gauge → 0; 5xx spike on `/v1/ask` | Provider fallback chain + circuit breaker (`core/llm_client.py`, `core/resilience.py`); degraded snippet-synthesis mode with disclosure |
| FM-02 | Search API (Tavily/SerpAPI) outage or throttling | 429/5xx from provider | Answers lack fresh web grounding | `tool_result_total{tool=web_search,error=1}` ratio | Second provider configured; CB per provider; cached answers still served |
| FM-03 | Cascade amplification (retry storms) | Naive retries × in-flight requests multiply during partial outage | Whole cluster saturates; healthy requests starve | Retry-rate vs error-rate divergence; queue depth | Retries are capped, jittered, budgeted (`core/resilience.py`); CB opens before amplification; singleflight collapses duplicates |
| FM-04 | Cache stampede on hot/trending query | Popular query TTL expires / news event | 1000s of identical upstream computations | `cache_hit_ratio` cliff; LLM call-rate spike | Singleflight lock per key (one compute, rest wait); stale-while-revalidate; jittered TTLs (`api/cache.py`) |
| FM-05 | Redis unavailable | Node failover, network partition | Cache, rate limits, locks, A2A store degrade | `redis_up` = 0; middleware alarms | Cache fails open (serve fresh), rate limiter falls back to in-process window, A2A falls back to in-memory store — service stays up, correctness of limits degrades (documented) |
| FM-06 | Runaway agent (infinite ReACT loop / reflection cycles) | Model repeats tool calls; adversarial prompts | High latency + $ per request; worker exhaustion | `budget_exceeded_total`; p99 latency spike | `core/budgets.py` hard caps tokens/tool-calls/steps/wall-clock per request; `MaxIterationsExceededError` → 422 with partial answer when possible |
| FM-07 | Cost explosion via expensive strategies | Tree-search/Reflexion selected for trivial queries | Margin erosion (S2) | `request_cost_usd` histogram p99 | Router prefers cheap strategies; budget caps; usage tracker (`core/usage_tracker.py`) alerts on per-request cost |
| FM-08 | SSRF / internal metadata access via tool calls | Prompt-injected URL (`http://169.254.169.254/…`, `10.x`, `127.0.0.1`) | Credential theft → full compromise (S1 security) | `ssrf_blocked_total` counter | `tools/ssrf_guard.py`: scheme allowlist, private/loopback/link-local IP deny, redirect re-validation, response size cap |
| FM-09 | Oversized response body (zip-bomb page, huge JSON) | Malicious/slow target page | Worker memory blow-up, OOM kills | Pod OOMKilled events; `tool_result_truncated_total` | Hard byte caps on fetch (`max_response_bytes`), truncation markers, streaming parse aborts |
| FM-10 | SSE connection exhaustion | LB idle timeout < stream duration; clients hold sockets | New users rejected; LB 502s | Concurrent-connection gauge; accept-queue drops | Heartbeats (`api/streaming.py`), per-user connection caps, documented LB tuning (idle ≥ 75s), client backoff protocol |
| FM-11 | Event-loop blocking (sync work in async path) | `BeautifulSoup` parse of 10MB page on main loop; tiktoken in hot loop | Latency for all requests on that worker | p99 event-loop lag metric | Heavy parsing offloaded to thread pool (`asyncio.to_thread`); encoder cached at class level (`core/token_counter.py`) |
| FM-12 | Poison task crashes async workers | Malformed task / rare exception path | Worker crash-loop; queue backlog | Worker restart count; DLQ depth | try/except at task boundary, max-delivery count, dead-letter stream, task TTL (`agents/a2a_server.py`) |
| FM-13 | Race: parallel workers overwrite shared state | Orchestrator workers mutate shared registry/state | Subtle wrong answers (S2) | Correlation-ID trace mismatch | Workers own isolated state copies; registry is read-only after startup; `asyncio.gather(return_exceptions=True)` isolates failures |
| FM-14 | Partial provider response (truncated JSON from LLM) | Output token limit hit mid-JSON | Parse errors surface as 500s | `plan_parse_failures` counter | Defensive JSON extraction with fallback plans (planner/routing); finish_reason surfaced in metadata; retry-with-shrink on truncation |
| FM-15 | Hallucinated / ungrounded answers | Model ignores snippets; citations missing | Trust erosion (product S1 over time) | `evaluation` citation-coverage gate in CI; `/v1/evaluate` sampled in prod | Answer-level citation metrics (`evaluation/metrics.py`), reflection pass on low-coverage answers, golden-set regression gate |
| FM-16 | Secret leakage into logs | Debug logging of full payloads containing keys | Credential exposure (S1 security) | Log scanner alerts | `SecretStr` everywhere; redaction processor in `configs/logging_config.py`; CI secret scan |
| FM-17 | Deployment regression (bad image) | Config drift, missing env var | Crash-loop on rollout | Readiness probe failures; rollback alarm | Multi-stage Dockerfile with smoke-tested healthcheck; K8s `maxUnavailable: 0`, readiness gates, `docker-publish.yml` runs smoke test before tag |
| FM-18 | DNS / connection churn to providers | New httpx client per request (old pattern) | Socket exhaustion, +50ms per call latency | `http_connection_reuse_ratio`; ephemeral-port pressure | Shared pooled client with keep-alive (`tools/http_client.py`) |

## Cross-cutting rules (how we keep this list from growing)

1. **Every new external dependency gets:** a timeout, a circuit breaker, a
   budget line, and an alert — before it ships.
2. **Every new loop gets:** a max-iteration bound AND a wall-clock budget.
3. **Every new cache gets:** a TTL, jitter, and a stampede story.
4. **Every new outbound URL gets:** the SSRF guard.
5. **Every incident updates this file** — new FM row or updated mitigation
   within 48h (see `docs/POSTMORTEM-TEMPLATE.md`).
