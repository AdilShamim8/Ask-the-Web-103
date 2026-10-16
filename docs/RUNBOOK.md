# On-Call Runbook

**Last updated:** 2026-10-16 · **Audience:** on-call engineer

The golden rule: **check the FMEA register first**
(`docs/architecture/failure-mode-analysis.md`) — the incident you're in is
probably FM-0x with a mitigation already designed.

## Triage in 60 seconds

1. Is `/healthz` failing fleet-wide? → **FM-17 / deploy regression** → roll
   back (below). Don't debug forward at 3am.
2. Are 5xxs spiking on `/v1/ask` with providers down? → **FM-01/02** →
   check breaker panel, confirm degraded mode is serving.
3. Latency up, error rate flat? → **FM-04/10/11** → cache ratio panel,
   SSE concurrency gauge, event-loop lag.
4. Cost alerts? → **FM-06/07** → budget-exceeded panel, top queries by USD.

## Key dashboards & queries (Prometheus)

| Symptom | Query |
| ------- | ----- |
| Availability | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| Provider health | `llm_provider_up`, `circuit_breaker_state` by provider |
| Cache effectiveness | `sum(rate(cache_hits_total[5m])) / sum(rate(cache_requests_total[5m]))` |
| Stampede pressure | `rate(singleflight_duplicates_total[5m])` |
| Runaway agents | `rate(budget_exceeded_total[5m])` by reason |
| Per-request cost | `histogram_quantile(0.99, rate(request_cost_usd_bucket[5m]))` |
| Tool failures | `rate(tool_result_total{is_error="true"}[5m])` by tool |

## Common incidents

### INC-1 · LLM provider down (FM-01)
1. Confirm: `llm_provider_up{provider="openai"} == 0` for > 1 min.
2. Verify breaker opened: `circuit_breaker_state{provider="openai"} == 2`.
3. Traffic should have shifted to fallback automatically — verify
   `llm_provider_selected_total` moved.
4. If BOTH providers down: expect degraded snippet answers (flag
   `degraded_mode` in responses). Announce status page. Do NOT retry-storm
   manually.
5. Recovery: breaker goes half-open after 60s; watch error rate before
   declaring resolved.

### INC-2 · Redis unavailable (FM-05)
1. Symptom: `redis_up == 0`; latency +L2 miss rate = 100%.
2. Service is DESIGNED to fail open: cache/locks/A2A store degrade to
   in-memory. Confirm no crash-loops (pod restarts).
3. Fix Redis (provider console / failover). On recovery, singleflight locks
   expire via TTL — no manual cleanup needed.
4. Post-incident: check for duplicate LLM spend during the window.

### INC-3 · Cache stampede on trending query (FM-04)
1. Symptom: `cache_hit_ratio` cliff + LLM call rate 5–10× normal on ONE
   key family.
2. Mitigation: temporarily raise L2 TTL for hot keys
   (`REDIS_TTL_HOT_OVERRIDE`), or pre-warm:
   `scripts/smoke_test.sh --warm "trending query"`.
3. If singleflight locks are failing (check
   `singleflight_lock_errors_total`), it's a Redis issue → INC-2.

### INC-4 · Runaway agent / cost spike (FM-06/07)
1. Symptom: `budget_exceeded_total` > 2% or cost p99 alarm.
2. Identify top offenders: `topk(10, sum by (query_hash)
   (rate(request_cost_usd_sum[15m])))`.
3. Immediate: lower `MAX_*` budget env vars (hot-reloads on next request;
   no restart needed).
4. If adversarial: enable per-tenant quotas (rate-limit tier), consider
   blocking the query pattern in the router fast-path.

### INC-5 · Pod crash-loop / bad deploy (FM-17)
1. `kubectl rollout undo deployment/ask-web-api` — target recovery < 2 min.
2. Confirm image digest in the bad release; open rollback PR with
   `fix: revert` prefix.
3. Root-cause in postmortem (template: `docs/POSTMORTEM-TEMPLATE.md`)
   within 48h.

## Escalation

| Severity | Response | Notify |
| -------- | -------- | ------ |
| S1 (down / security) | 15 min, all hands | maintainer + status page |
| S2 (degraded) | 1 h business time | maintainer |
| S3 (toil/latent) | next sprint | issue ticket |

Security incidents follow `SECURITY.md` — never discuss details in public
issues.

## Post-incident obligations

1. Update the FMEA row (or add a new one) — what fired, what didn't.
2. If a mitigation failed, file the fix with a test reproducing the gap.
3. Share numbers: blast radius, duration, cost impact, MTTR.
