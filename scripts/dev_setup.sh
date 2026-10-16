#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# dev_setup.sh — one-shot local development bootstrap. Idempotent.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${YELLOW}▶${NC} $1"; }
ok()   { echo -e "${GREEN}✓${NC} $1"; }
die()  { echo -e "${RED}✗${NC} $1"; exit 1; }

info "Checking Python version (need >= 3.11)"
command -v python3 >/dev/null || die "python3 not found"
PYV=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" \
    || die "Python $PYV found, 3.11+ required"
ok "Python $PYV"

info "Creating virtual environment (.venv)"
[[ -d .venv ]] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
ok "venv active"

info "Installing project + dev dependencies"
pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"
ok "dependencies installed"

info "Installing Playwright chromium (for the scraper)"
if playwright install chromium; then
    ok "chromium ready"
else
    echo -e "${YELLOW}  playwright install failed — scraper fallback disabled (non-fatal)${NC}"
fi

info "Writing .env from template (if missing)"
if [[ ! -f .env ]]; then
    cp .env.example .env
    echo -e "${YELLOW}  .env created — add your API keys before running the agent${NC}"
else
    ok ".env already exists"
fi

info "Installing pre-commit hooks"
pre-commit install && ok "pre-commit installed" || true

info "Running the test suite (no provider keys needed)"
if python -m pytest tests/ -q > /tmp/askweb_tests.log 2>&1; then
    ok "test suite green"
else
    tail -20 /tmp/askweb_tests.log
    die "test suite failed — see /tmp/askweb_tests.log"
fi

echo
echo -e "${GREEN}Setup complete.${NC} Next steps:"
echo "  1. Add real API keys to .env (at least one LLM + one search provider)"
echo "  2. make dev-redis     # optional: local cache/rate-limit backend"
echo "  3. make dev           # run the API on :8000"
echo "  4. ./scripts/smoke_test.sh"
