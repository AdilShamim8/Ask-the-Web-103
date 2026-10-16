# ── Ask-the-Web developer entrypoint ─────────────────────────────────────────
# Every command CI runs exists here first: if it's red locally, it's red
# on GitHub. See CONTRIBUTING.md.

.DEFAULT_GOAL := help
.PHONY: help dev test lint typecheck compile eval clean docker-build docker-up docker-down

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ── Development ───────────────────────────────────────────────────────────────

dev: ## Run the API locally with hot reload
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

dev-redis: ## Start a local Redis (background)
	docker run -d --name askweb-redis -p 6379:6379 redis:7-alpine || true

# ── Quality gates (mirror CI) ─────────────────────────────────────────────────

lint: ## Ruff lint
	ruff check .

format: ## Ruff auto-format
	ruff format .
	ruff check --fix .

typecheck: ## Mypy
	mypy core tools agents workflows api evaluation --ignore-missing-imports

compile: ## Byte-compile every module (import-parse gate)
	python -m compileall -q core configs tools agents workflows api evaluation tests

test: ## Full test suite
	pytest tests/ -v

test-cov: ## Test suite with coverage report
	pytest tests/ --cov=core --cov=tools --cov=workflows --cov=agents --cov=api \
		--cov-report=term-missing --cov-fail-under=50

eval: ## Run the golden-set eval gate (needs provider keys)
	python -m evaluation.benchmarks

gate: lint compile test ## Everything CI requires minus docker

# ── Containers ────────────────────────────────────────────────────────────────

docker-build: ## Build the production image
	docker build --target runtime -t ask-the-web:local .

docker-up: ## Local stack (app + redis + prometheus)
	docker compose up --build -d

docker-down: ## Stop the local stack
	docker compose down

# ── Hygiene ───────────────────────────────────────────────────────────────────

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
