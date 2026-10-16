# ADR-002: Provider abstraction with health-weighted fallback

**Status:** Accepted · **Date:** 2026-10-16

## Context

Ask-the-Web calls two LLM providers (OpenAI, Anthropic) and two search
providers (Tavily, SerpAPI). At production scale any single vendor will
throttle, have an incident, or change pricing. The original code chose the
provider from settings once (`SEARCH_PROVIDER=tavily`) and had no fallback —
one vendor 429 storm would cascade into user-facing 5xxs (FM-01/FM-02).

## Decision

1. One `Provider` contract per capability with an **ordered preference
   list** (`llm_provider_order`, `search_provider_order` in settings), not a
   single choice.
2. Every call goes through the shared resilience wrapper: bounded jittered
   retries **inside** a per-provider circuit breaker. When a breaker is
   open, the provider is skipped instantly (no latency penalty).
3. Breakers are health-weighted: after recovery, only a trickle of traffic
   (half-open probes) returns until success rate stabilizes.
4. Model tiering: `default_model` for synthesis, `fast_model` for routing /
   classification / tool selection — cost is part of the routing decision
   (see capacity doc: routing cheap calls to small models ≈ $84M/yr saved).

## Alternatives considered

- **Client-side LB across providers with round-robin:** rejected — provider
  latency/cost profiles differ wildly; preference order + breakers is
  simpler and predictable under incident.
- **Per-request dynamic vendor bidding:** rejected for 2.0 — needs usage
  telemetry we only just built. Tracked as 2.x roadmap item.

## Consequences

- `LLMClient.complete()` gains `provider_hint`; actual provider selection is
  internal and observable (`llm_provider_selected_total` counter).
- Provider-specific quirks (Anthropic tool-call format, system prompts)
  stay inside `core/llm_client.py` — agents never know which vendor ran.
- Tests inject a fake provider list; breaker states are unit-testable with
  a fake clock.
