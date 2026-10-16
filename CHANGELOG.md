# Changelog

All notable changes to Ask-the-Web are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/).

## [2.0.1] — 2026-10-16

Patch release: full CI/CD green-wall restoration plus a self-found
bug sweep (14 fixes). Every check that was red at v2.0.0 is green.

### Fixed — Build & CI (the five red checks)
- **Packaging**: hatchling could not discover any package — every
  `pip install` (CI typecheck/tests, Docker builder) died at
  metadata generation. `[tool.hatch.build.targets.wheel]` now ships
  the seven real top-level packages.
- **Docker build**: LICENSE was dockerignored while pyproject
  requires it; the builder needed stub packages present; [dev] extras
  no longer ship to production.
- **trivy**: build/install tooling (venv-seeded setuptools/wheel,
  pip-vendored urllib3/msgpack, ensurepip bundles) purged from the
  runtime image; secret-scanner false positives dropped
  (scanners: vuln); the purge is version-agnostic for base bumps.

### Fixed — Code (self-found)
- openai SDK v3 removed `text_stream` — streaming answers were dead
  (AttributeError on every call); rewritten on the chunked transport.
- SecretStr fields had bare str defaults — unset env vars surfaced
  raw strs and crashed `.get_secret_value()`.
- Playwright driver subprocess leaked whenever browser launch failed.
- Playwright browsers installed as root were unreadable by appuser —
  scraping was silently dead in the published image.
- ReWOO's budget clamp was dead code (F841); now sizes plans to the
  remaining step budget.
- B023 late-binding closures in both provider fallback chains;
  B905 silent zip misalignment in fan-outs; F821 unresolved
  annotations in the MCP client.
- Blind `pytest.raises(Exception)` hid that a test never ran its
  code under test (deprecated event-loop API raised first).
- Version strings unified to `core.__version__` (schemas had drifted
  to a hardcoded '2.0').

### Changed
- CI typecheck promoted from `continue-on-error` to a hard gate:
  mypy reports zero findings across 55 source files.
- StrEnum migration: `str(member)` now matches on py3.11 AND py3.12.

## [2.0.0] — 2026-10-16

The production re-architecture: same course lineage, production spine.
Executed as a 108-commit hardening program (one logical change per
commit, see `git log --grep "Commit-Ref"`).

### Added — Architecture & Operations
- **Architecture documentation set**: `docs/ARCHITECTURE.md` (C4 system,
  container, component views), capacity planning & unit economics for
  100–200M DAU (`docs/architecture/capacity-planning.md`), failure-mode
  register with 18 FMEA entries (`docs/architecture/failure-mode-analysis.md`),
  request lifecycle (`docs/architecture/request-lifecycle.md`), and five
  Architecture Decision Records (ADR-001…005).
- **On-call runbook** (`docs/RUNBOOK.md`) with incident playbooks IN-1…IN-5,
  dashboard queries mapped to FMEA rows, and an escalation matrix.
- **Deployment guide** (`docs/DEPLOYMENT.md`) with rollout-safety
  parameters and production configuration checklist.
- **Security policy** (`SECURITY.md`) with a threat-model table mapping
  each threat to its in-code mitigation.

### Added — Core reliability
- **Request budgets** (`core/budgets.py`): per-request token, tool-call,
  step, and wall-clock ceilings; runaway agents terminate with a partial
  answer instead of hanging (FMEA FM-06/07, ADR-005).
- **Resilience primitives** (`core/resilience.py`): circuit breakers
  (closed/open/half-open with failure-rate tripping), bounded full-jitter
  retries, and token-bucket rate limiting.
- **Usage & cost accounting** (`core/usage_tracker.py`): per-request USD
  estimation, per-model pricing table, Prometheus export; API responses
  now disclose what they consumed.
- **Observability** (`core/observability.py`): RED metrics for HTTP, LLM,
  tools, cache, agents, and breaker states — every series is referenced
  by a runbook query.
- **Provider fallback chains** (`core/llm_client.py`): ordered provider
  preference with per-provider breakers; an OpenAI incident no longer
  fails the request when Anthropic is healthy (FM-01).

### Added — Tool safety
- **SSRF guard** (`tools/ssrf_guard.py`): scheme allowlist, private/
  link-local/loopback IP blocking, DNS-resolution pinning, redirect
  re-validation, byte caps on streamed bodies (FM-08/09).
- **Shared HTTP pool** (`tools/http_client.py`): keep-alive connections
  replace per-request client construction (FM-18).
- **Hardened executor** (`tools/tool_executor.py`): argument validation,
  per-call timeouts, result truncation, budget hooks, metrics — enforced
  centrally so no tool can opt out.
- **MCP server** (`tools/mcp_server.py`): the tool registry is now
  exposed over MCP for external assistants, with all guards applied
  (ADR-004).
- **MCP client hardening**: session reuse, TTL tool-discovery cache,
  self-healing re-handshake, per-server breakers.

### Added — Workflows, agents, protocols
- **Orchestrator-worker workflow** (`workflows/orchestrator_worker.py`):
  deterministic fan-out with worker isolation and partial degradation.
- **A2A task server** (`agents/a2a_server.py`): Redis-backed task store
  with TTLs and result caps replaces the volatile in-memory dict (FM-12).
- **A2A coordinator** (`agents/a2a_coordinator.py`): isolated parallel
  delegation with per-agent breakers and deadline propagation.
- **Planner DAG validation** (`agents/planner.py`): cycle detection and
  dependency checks reject impossible plans before dispatch.
- All agents (ReACT, Reflexion, ReWOO, TreeSearch, Orchestrator) now
  share budgets, report usage, and degrade instead of crash.

### Added — API production surface
- **Two-layer cache with singleflight + stale-while-revalidate**
  (`api/cache.py`): cache stampedes collapse to one compute (ADR-003).
- **Redis sliding-window rate limiting** with per-IP fallback, security
  headers, and typed error responses with stable error codes.
- **SSE streaming with heartbeats** (`api/streaming.py`): idle-safe
  through proxies, client-disconnect aware, hard stream deadline (FM-10).
- **Cheap health probes**: `/v1/healthz` (liveness, no provider calls —
  the 1.0 health check made a paid LLM call per probe) and `/v1/readyz`
  (deep readiness for K8s).
- **Request-scoped DI** (`api/dependencies.py`) — test seams and clean
  wiring for budgets/usage.

### Added — Quality & infrastructure
- **Test suite grown 66 → 158 tests**, all green, including regression
  suites for stampede protection, SSRF attacks, budget exhaustion, worker
  isolation, and breaker behavior.
- **CI pipeline**: ruff → mypy → pytest with coverage gate → image build
  → boot smoke test; security pipeline: pip-audit, gitleaks, trivy.
- **Kubernetes manifests**: zero-downtime deployment (maxUnavailable=0,
  45s SSE drain), HPA, PDB, NetworkPolicy, hardened security contexts.
- **Golden evaluation dataset** (`evaluation/datasets/golden_v1.json`)
  with a CI quality gate; citation-precision metric catches fabricated
  citations (FM-15).
- Makefile, pre-commit, dependabot, PR template, issue templates,
  postmortem template, dev/smoke scripts.

### Fixed
- **Dockerfile**: runtime stage now installs `curl` — the healthcheck
  called a binary that only existed in the builder stage, so every probe
  failed while the app was healthy (FM-17).
- **docker-compose**: removed deprecated `version:` key; the prometheus
  service mounted `configs/prometheus.yml`, which did not exist in the
  repo — the file now exists (compose monitoring was silently broken).
- **structlog**: removed `stdlib.add_logger_name` processor —
  incompatible with `PrintLoggerFactory`, it crashed the first
  application log call after startup (found by the test suite).
- **Calculator on Python 3.12+**: AST allowlist was missing `ast.Load`/
  `ast.Store` context nodes, rejecting every function-call expression on
  modern Python.
- **Anthropic SDK compatibility**: current SDKs reject `temperature` on
  some models; the client retries once without sampling parameters.
- **A2A task store**: oversized results are capped at the payload level —
  string-level truncation produced unparseable JSON.
- **ReWOO evidence substitution**: evidence snippets are JSON-escaped;
  unresolvable steps are skipped instead of executing with corrupted args.
- **Secret hygiene**: `.gitignore`, log redaction processor, `SecretStr`
  everywhere; CRLF line endings from web uploads normalized to LF.

### Changed
- API version 2.0: responses carry `api_version`, `usage`, `budget`,
  `degraded`, `degradation_reasons`.
- Max-iterations exhaustion now returns a degraded partial answer
  (HTTP 200 with `degraded: true`) instead of raising 422 — degrade,
  don't die.
- Tool errors return structured JSON `{"error": ...}` instead of prose.
- `app_env` defaults to `development` — production must be explicit.
- LLM calls accept a `fast=True` tier for routing/classification work
  (cost split worth ~$84M/yr at target scale per capacity doc).

## [1.0.0] — 2026-06-04

Initial course release: ReACT, Reflexion, ReWOO, Tree Search, MCP,
A2A, FastAPI surface, Redis cache, Prometheus, evaluation harness.
