# Release Notes — v2.0.0 (2026-10-16)

**Ask-the-Web 2.0: the production re-architecture.**

The course project grew a production spine. Same educational lineage,
same five agent strategies, same protocols — now with the guarantees a
real product needs at scale.

## The one-paragraph story

We treated this repo as a product serving 100–200M daily users, found
every place it would break (18 documented failure modes), and fixed
them: every request now carries a budget so nothing runs away; every
provider call sits behind a circuit breaker and a fallback chain so no
vendor outage takes us down; every tool call passes an SSRF guard, a
timeout, and a size cap so hostile web content can't hurt us; every
cache miss is singleflight-protected so traffic spikes don't multiply
into stampedes; and when things do degrade, users get honest partial
answers with disclosures instead of errors.

## Headline guarantees

| Guarantee | Mechanism | Proof |
| --------- | --------- | ----- |
| Bounded requests | `core/budgets.py` (ADR-005) | `tests/test_budgets.py::test_runaway_agent_terminates` |
| Provider-outage survival | Breakers + fallback chains (ADR-002) | `tests/test_resilience.py` |
| SSRF-immune tool execution | `tools/ssrf_guard.py` (FM-08) | `tests/test_ssrf_guard.py` |
| Stampede-proof caching | Singleflight + SWR (ADR-003) | `tests/test_cache.py::test_only_one_compute_under_concurrency` |
| Worker-failure isolation | FM-13 patterns | `tests/test_orchestrator_worker.py`, `tests/test_a2a.py` |
| Cost observability | `core/usage_tracker.py` | `tests/test_usage_tracker.py` |

## Real bugs the program found and fixed

1. Docker healthcheck invoked `curl` missing from the runtime image —
   every probe failed while the app was healthy.
2. `configs/prometheus.yml` referenced by compose but never committed —
   monitoring was silently broken.
3. structlog processor combination crashed the first log call after
   startup.
4. Calculator tool broken on Python 3.12+ (AST allowlist gap).
5. Current Anthropic SDK rejects `temperature` — now degrades gracefully.
6. A2A result truncation produced unparseable JSON.
7. Reflection workflow reached into private attributes (fragile coupling).

Full detail: [`CHANGELOG.md`](../CHANGELOG.md).

## The numbers

- **108 commits**, one logical change each (`git log --grep "Commit-Ref"`)
- **158 tests passing** (up from 66), zero provider keys required
- **18 failure modes** documented with in-code mitigations
- **5 ADRs** + architecture, capacity, runbook, deployment, security docs
- **~9,200 lines** of hardened, documented, tested production code

## Upgrading from 1.0

- API responses add `api_version`, `usage`, `budget`, `degraded`,
  `degradation_reasons` — additive, existing clients keep working.
- Errors now return stable `error` codes (see `core/exceptions.py`).
- `APP_ENV` defaults to `development`; set it explicitly in prod.
- Environment additions are documented in `.env.example` — budgets,
  cache tuning, tool safety, provider order.
