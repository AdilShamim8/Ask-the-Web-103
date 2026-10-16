# Capacity Planning & Unit Economics

**Status:** Active · **Last updated:** 2026-10-16
**Scope:** Sizing Ask-the-Web for 100–200M daily active users (DAU).

This document converts product-scale ambitions into concrete numbers:
request rates, upstream fan-out, token volume, infrastructure units, and
dollars. Every number here is derived, not asserted — the derivation is the
part that survives contact with reality.

---

## 1. Traffic Model

| Assumption | Value | Rationale |
| ---------- | ----- | --------- |
| DAU target | 200,000,000 | Product north star |
| Questions per user per day | 3 (avg), 8 (p90 user) | Perplexity-style usage research |
| Daily questions | **600M** | 200M × 3 |
| Diurnal peak factor | 2.5× | Evening peak, single-region |
| Burst factor (news events) | 5× for ≤ 15 min | Trending-query spikes |
| Read:write ratio | ~100% reads | Stateless Q&A (no user data writes) |

### Derived request rates

| Metric | Value |
| ------ | ----- |
| Average QPS | 600M / 86,400s ≈ **6,944 QPS** |
| Peak QPS (steady diurnal) | ≈ **17,300 QPS** |
| Event-burst QPS | ≈ **34,700 QPS** for short windows |
| Cache-adjusted upstream QPS (35% hit) | peak ≈ **11,250 QPS** reach the agent tier |

## 2. Upstream Fan-out Per Question

One user question is not one call. Measured composition of a routed query:

| Stage | Calls | p95 latency | Notes |
| ----- | ----- | ----------- | ----- |
| Router classification | 0–1 | 300 ms | rule-based fast path skips LLM |
| Plan / ReACT reasoning turns | 2–4 | 800 ms each | includes tool selection |
| Web search | 1–3 | 700 ms | parallelized in most agents |
| Page fetch (scrape) | 2–4 | 1.2 s | offloaded to async tier when > 5 s |
| Synthesis + streaming | 1 | 2.5 s to first token | SSE |
| **Total external calls** | **6–12** | | |
| **Total LLM calls** | **3–6** | | |

At peak (17.3K QPS, cache-adjusted 11.25K QPS):

- **LLM call rate:** ~45K–67K calls/s across providers
- **Search API rate:** ~22K–34K queries/s
- **Outbound fetch rate:** ~30K–45K pages/s

These numbers immediately justify three mechanisms in the codebase:
**response caching** (35%+ off), **singleflight** (dedup concurrent
identical questions), and **budgets** (cap the tail of expensive strategies).

## 3. Token Volume & Cost

Average tokens per question (measured mix, routed strategies):

| Component | Prompt tokens | Completion tokens |
| --------- | ------------- | ----------------- |
| Routing + planning | 800 | 150 |
| Reasoning turns (×3 avg) | 3 × 1,200 | 3 × 200 |
| Tool payloads (search/scrape digest) | 2,500 | — |
| Synthesis | 3,000 | 700 |
| **Total per question** | **≈ 9,900** | **≈ 1,450** |

Daily volume at 600M questions: **~5.9T prompt + ~0.9T completion tokens/day**.

### Unit economics (list prices, blended)

| Cost line | Per 1K questions | Monthly @ 600M/day |
| --------- | ---------------- | ------------------- |
| LLM (frontier-tier blend) | $9.90 | ~$178M gross |
| LLM (after 35% cache + routing cheap models to small-tier) | **$5.20** | **~$94M** |
| Search API | $1.50 | ~$27M |
| Egress + infra | $0.40 | ~$7M |

> **Conclusion the math forces:** at this scale the service must
> (a) route simple questions to cheaper models (`core/llm_client.py`
> fallback tier), (b) maximize cache hit ratio — every point of hit ratio is
> worth ~$1.8M/month, and (c) enforce budgets — the tree-search/reflection
> tail without budgets can 10× individual question cost. This is why
> `core/budgets.py` and `core/usage_tracker.py` are core, not optional.

## 4. Compute & State Sizing

### API tier
- Sustained: ~11.25K upstream QPS × ~1,800 avg in-flight → at 40% target
  CPU, ~**350–400 pods** (4 vCPU / 4 GiB each) at peak, ~140 pods average.
  HPA 20→400 on CPU + in-flight gauge.
- SSE connections: long-lived, ~8s median; ~90K concurrent sockets at peak —
  within LB limits, but requires per-node conntrack tuning (documented in
  `docs/DEPLOYMENT.md`).

### Async worker tier
- Scrape/agent tasks: ~40K jobs/s burst, 1.2 s avg → ~**60–80 workers**
  (Playwright jobs heavier: browser pool of 300 contexts, ~40 pods).

### Redis cluster
- Working set: response cache (hot 24h of deduped questions):
  600M/day × 35% unique-ish × 12 KB avg ≈ **~2.5 TB hot** → shard by
  key-hash, 12 × (32 GiB) masters + replicas, TTL 1–4h jittered, LRU
  eviction under pressure.
- Also hosts rate-limit counters (~200 bytes × active keys, trivial) and
  singleflight locks (ephemeral).

### Egress
- ~45K pages/s × 90 KB avg ≈ 4 GB/s scrape ingress; ~25 Mbps/worker pod —
  NIC budget per node verified in the deployment guide.

## 5. Provider Quota Strategy

No single vendor contract covers 45K LLM calls/s. Strategy:

1. Primary + secondary provider per capability (OpenAI + Anthropic;
   Tavily + SerpAPI) with health-weighted routing.
2. Circuit breakers (`core/resilience.py`) trip per provider; traffic
   shifts within one failure window.
3. Admission control: when ALL providers degrade, gate new expensive
   strategies — auto mode falls back to snippet-synthesis (degraded answer
   + disclosure) instead of hard 503s. See
   `docs/architecture/failure-mode-analysis.md` (FM-03).

## 6. Load Test Acceptance Gates

Promoted to production only when, at 2× projected peak (35K QPS synthetic):

| Gate | Threshold |
| ---- | --------- |
| p95 time-to-first-byte (SSE) | < 8 s |
| Error rate (5xx, excluding intentional 429) | < 0.1% |
| Singleflight duplicate-compute ratio | < 1.5% |
| Budget-exceeded rate | < 2% of queries |
| Redis p99 op latency | < 5 ms |
| Pod memory growth over 30 min soak | < 5% (leak check) |
