# ADR-003: Two-layer response cache with singleflight and stale-while-revalidate

**Status:** Accepted · **Date:** 2026-10-16

## Context

Answer generation costs $0.005–$0.05 per question and 3–8 seconds of
latency. Identical questions recur heavily (trending news, common facts).
The original cache was Redis-only, get-then-compute with no coordination:
on a hot key expiry, every pod computed the same answer simultaneously
(cache stampede, FM-04) — enough duplicate LLM spend to matter at scale,
and enough duplicate load to tip providers into throttling.

## Decision

1. **L1 in-process LRU** (per-pod, ~30s TTL) absorbs request bursts from
   the same pod; **L2 Redis** (jittered 1–4h TTL) is the shared truth.
2. **Singleflight:** on L2 miss, acquire `SET key:lock <pod> NX PX 8000`.
   Winner computes; losers wait up to N ms polling the key, then read the
   fresh value. Exactly one upstream computation per key per expiry cycle.
3. **Stale-while-revalidate:** values carry a soft TTL; a stale hit is
   served immediately while a background refresh runs. Users never wait on
   a refresh, freshness converges within minutes.
4. **Versioned key prefix** (`ask_web:v2:`) so a cache-format change is a
   prefix bump, not a fleet flush.
5. **Fail-open:** if Redis is down, we serve fresh answers (correctness of
   freshness degrades, availability does not — FM-05).

## Alternatives considered

- **Full-page CDN caching at edge:** rejected as primary layer — request
   bodies (POST), per-user personalization, and auth vary; CDN remains for
   static assets only.
- **Semantic/embedding cache (near-duplicate questions):** promising at
  200M-DAU scale (~10–20% additional hit ratio) but adds an embedding
  index and a similarity threshold that can silently serve wrong answers.
  Deferred to 2.x with an eval gate.

## Consequences

- `api/cache.py` becomes the single implementation; no ad-hoc `redis.get`
  in routes.
- Tests must cover the stampede path (N concurrent misses → 1 compute).
- Cache hit ratio is a primary SLO (≥ 35%) with its own dashboard panel.
