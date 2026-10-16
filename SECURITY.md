# Security Policy

**Last updated: 2026-10-16**

## Supported Versions

| Version | Supported          | Status |
| ------- | ------------------ | ----- |
| 2.0.x   | ✅ Active          | Current production line |
| 1.0.x   | ⚠️ Best effort     | Legacy course build |

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, use GitHub's private vulnerability reporting on this repository
(*Security → Report a vulnerability*), or email the maintainer directly.
Please include:

1. The type of issue (e.g., SSRF, injection, credential leak, DoS vector)
2. Full paths of affected files and proof-of-concept steps
3. Potential impact and suggested mitigation if you have one

We aim to acknowledge reports within **48 hours** and triage within
**5 business days**. Valid SSRF / RCE / credential-leak reports in the
tool-execution path are treated as **P1**.

## Security Model & Threat Surface

This service executes LLM-directed tool calls against the public internet.
That makes it an execution surface by design. The main threats and our
mitigations:

| Threat | Mitigation (file) |
| ------ | ----------------- |
| SSRF via `scrape_webpage` / MCP tools fetching internal metadata endpoints (`169.254.169.254`, `10.x`, `127.0.0.1`) | `tools/ssrf_guard.py` — scheme allowlist, private/link-loopback IP blocking, redirect re-validation, response size caps |
| Cost-exhaustion (a hostile prompt driving tree-search / reflection loops into unbounded LLM spend) | `core/budgets.py` — per-request token, tool-call, step, and wall-clock budgets; enforced before every LLM and tool call |
| Credential leakage into logs | `configs/logging_config.py` — key redaction processor; `SecretStr` everywhere in `configs/settings.py` |
| Rate-limit bypass via multiple pods with in-memory-only limiters | Redis-backed sliding-window limiter in `api/middleware.py` with per-instance local fallback |
| Container escape surface | Runtime stage ships no build toolchain, runs as non-root `appuser`, image scanned in CI (`security.yml`) |
| Dependency CVEs | Dependabot + `pip-audit` gate in CI |

## Secrets Handling

- All secrets enter via environment variables (see `.env.example`).
- `.gitignore` blocks `.env*` (except the example), keys, and certs.
- Never bake provider keys into images — K8s Secrets / Docker secrets only.
- Rotate the `OPENAI_API_KEY` / `TAVILY_API_KEY` / `SERPAPI_API_KEY` quarterly
  and immediately after any suspected exposure.

## Dependency Policy

- Direct dependencies must be pinned to a minor range and reviewed on upgrade.
- `pip-audit` runs on every PR; high/critical advisories block merge.
- New runtime dependencies require an ADR explaining the need.
