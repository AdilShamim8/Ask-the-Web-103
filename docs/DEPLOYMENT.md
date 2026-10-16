# Deployment Guide

**Last updated:** 2026-10-16

Target environments: local (docker compose) → staging → production (Kubernetes).

## 1. Local development

```bash
cp .env.example .env      # fill keys
docker compose up -d redis
make dev                  # uvicorn --reload on :8000
```

Hot paths for iteration: `make test`, `make lint`, `make typecheck`.
No external provider keys are needed for the unit suite — fakes are
injected at the `core/` boundary (ADR-001).

## 2. Container images

- Multi-stage build: builder (toolchain) → runtime (no build tools,
  non-root `appuser`) — see `Dockerfile`.
- **Healthcheck:** the runtime stage ships a static-linked `curl` —
  the original image called `curl` without installing it in the runtime
  stage, so every healthcheck failed while the app was healthy (fixed
  2026-10-16; see CHANGELOG).
- Tags: `:sha-<commit>` on every CI build, `:vX.Y.Z` + `:latest` on
  release tags. Images are built by `.github/workflows/docker-publish.yml`
  which runs the smoke test BEFORE pushing the tag.

## 3. Staging → production rollout

1. CI green (lint, typecheck, unit, eval-gate, pip-audit).
2. Image deployed to staging via `deploy/k8s/` manifests with
   `IMAGE_TAG=sha-<commit>`.
3. Staging gates: `/healthz` 200 within 60s, error rate < 0.5% over 15-min
   soak, golden-set eval score ≥ threshold (`make eval`).
4. Production: `kubectl set image deployment/ask-web-api api=$IMAGE`
   with `maxUnavailable: 0` — surge pod must pass readiness before any old
   pod terminates.
5. Watch 15 min: 5xx ratio, p95 latency, budget-exceeded rate, cost p99.
   Any regression → `kubectl rollout undo` (INC-5).

### Rollout safety parameters (from `deploy/k8s/`)

| Parameter | Value | Why |
| --------- | ----- | --- |
| `maxSurge` | 25% | fast scale-up during deploy |
| `maxUnavailable` | 0 | never drop capacity below desired |
| `readinessProbe` | `/readyz` (checks Redis + config, NOT providers) | don't send traffic to a cold/broken pod |
| `livenessProbe` | `/healthz` (process-level, cheap) | restart wedged pods |
| `terminationGracePeriodSeconds` | 45 | drain in-flight SSE streams |
| `preStop` sleep | 10s | let LB deregister before SIGTERM |

## 4. Production configuration checklist

- [ ] `APP_ENV=production` (disables docs UI, switches log renderer to JSON)
- [ ] Redis cluster URL + auth (not the compose default)
- [ ] Both LLM + both search provider keys present (fallback chains armed)
- [ ] Budget env vars tuned to the tier (see `configs/settings.py` defaults)
- [ ] `RATE_LIMIT_*` set per tenant tier
- [ ] Prometheus scraping `:8000/metrics` (`configs/prometheus.yml`)
- [ ] Secrets via K8s Secret, never ConfigMap, never image
- [ ] HPA bounds reviewed (min 20 / max 400 pods for launch tier)
- [ ] LB idle timeout ≥ 75s (SSE streams; FM-10)
- [ ] Status page wired to `/healthz` external probe

## 5. Scaling operations

- **Scale event expected (launch, news):** pre-scale HPA min replicas,
  pre-warm top queries into cache, raise `MAX_*` budgets only if quality
  metrics allow.
- **Region expansion:** the API tier is stateless by construction; Redis
  and provider quotas are the only stateful dependencies — run regional
  Redis with async replication, and treat provider quotas as per-region
  budgets (capacity doc §5).

## 6. Database / state migrations

Redis key schema is versioned (`ask_web:v2:*`). Schema changes:

1. Ship code reading both old and new prefixes.
2. Deploy.
3. Remove old-prefix reads in the next release.
Never `FLUSHDB` in production — TTLs handle expiry; explicit mass-delete
only via runbook-reviewed script.
