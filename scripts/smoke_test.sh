#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# smoke_test.sh — fast end-to-end verification of a RUNNING deployment.
# Used by CI (image smoke) and by humans after deploys (runbook IN-3).
#
# Usage:
#   ./scripts/smoke_test.sh [BASE_URL]        # default http://localhost:8000
#   ./scripts/smoke_test.sh --warm "query"    # pre-warm the cache for a query
# Exit code 0 = all checks passed.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
info() { echo -e "${YELLOW}▶${NC} $1"; }

# ── Cache warm mode ───────────────────────────────────────────────────────────
if [[ "${1:-}" == "--warm" ]]; then
    QUERY="$2"
    BASE_URL="${3:-http://localhost:8000}"
    info "Warming cache for: $QUERY"
    curl -fsS -X POST "$BASE_URL/v1/ask" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$QUERY\", \"agent_type\": \"react\"}" > /dev/null \
        && pass "cache warmed" || fail "warm request failed"
    exit 0
fi

# ── 1. Liveness (cheap by contract) ───────────────────────────────────────────
info "liveness: GET /v1/healthz"
HEALTH=$(curl -fsS -m 5 "$BASE_URL/v1/healthz" 2>/dev/null) \
    && pass "liveness OK: $HEALTH" \
    || fail "liveness probe failed — pod should be restarted"

# ── 2. Readiness (deep checks) ────────────────────────────────────────────────
info "readiness: GET /v1/readyz"
READY=$(curl -fsS -m 10 "$BASE_URL/v1/readyz" 2>/dev/null) || READY=""
if [[ -n "$READY" ]]; then
    pass "readiness responded"
    echo "  $READY" | head -c 300; echo
else
    echo -e "${YELLOW}  readiness not configured or failed (non-fatal for smoke)${NC}"
fi

# ── 3. Validation contract (422 on bad input, not 500) ────────────────────────
info "validation: empty query must be 422"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/ask" \
    -H "Content-Type: application/json" -d '{"query": ""}')
[[ "$STATUS" == "422" ]] && pass "empty query → 422" || fail "expected 422, got $STATUS"

# ── 4. Security headers ───────────────────────────────────────────────────────
info "security headers on /v1/health"
HEADERS=$(curl -sI "$BASE_URL/v1/health")
echo "$HEADERS" | grep -qi "x-content-type-options" \
    && pass "security headers present" \
    || echo -e "${YELLOW}  security headers missing (older deployment?)${NC}"

# ── 5. Rate limiting exemptions (30 rapid health probes must all pass) ────────
info "rate limit: 30 rapid health probes (exempt path)"
ALL_OK=true
for _ in $(seq 1 30); do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 5 "$BASE_URL/v1/healthz")
    [[ "$CODE" == "200" ]] || ALL_OK=false
done
$ALL_OK && pass "monitoring path not rate-limited" || fail "healthz got throttled — check limiter exemptions"

# ── 6. Metrics endpoint ───────────────────────────────────────────────────────
info "metrics: GET /metrics"
curl -fsS -m 5 "$BASE_URL/metrics" > /dev/null \
    && pass "Prometheus metrics exposed" \
    || echo -e "${YELLOW}  /metrics not exposed (direct pod access may be required)${NC}"

echo
echo -e "${GREEN}All smoke checks passed.${NC}"
