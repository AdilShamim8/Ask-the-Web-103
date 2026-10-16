<!--
PR template — every field exists to make review fast and reviewable.
Delete sections that genuinely don't apply, but never the checklist.
-->

## Summary

<!-- One or two sentences: what changes and WHY. -->

## Change Type

- [ ] `feat` — new capability
- [ ] `fix` — bug fix
- [ ] `refactor` — no behavior change
- [ ] `perf` — performance only
- [ ] `docs` / `test` / `chore` / `ci`

## Impact Area

<!-- Which layer does this touch? Delete the rest. -->

- [ ] `core/` — LLM client, budgets, resilience, types
- [ ] `tools/` — tool registry, executor, web tools, MCP
- [ ] `agents/` / `workflows/` — reasoning strategies
- [ ] `api/` — HTTP surface, middleware, streaming
- [ ] `evaluation/` — quality harness
- [ ] `deploy/` / CI — infrastructure

## Production-Safety Checklist

<!-- Required for any change that can affect live traffic. -->

- [ ] No new unbounded loop, retry, or recursion — or it is wrapped in a budget
- [ ] Outbound HTTP goes through `tools/http_client.py` (pooled) and
      `tools/ssrf_guard.py` where URLs are user/LLM-influenced
- [ ] No secret values in code, logs, or test fixtures
- [ ] Graceful degradation verified: external dependency down → service still
      serves `/healthz` and degrades, does not crash-loop
- [ ] Tests added/updated; `make lint typecheck test` green
- [ ] Docs/CHANGELOG updated if user-visible or architectural

## Verification

<!-- How you proved it works: commands run, output, screenshots for API/UI. -->

```bash
# paste the commands + results you ran
```

## Related

<!-- Issues, ADRs, incidents. e.g. "Closes #12", "Implements ADR-003" -->
