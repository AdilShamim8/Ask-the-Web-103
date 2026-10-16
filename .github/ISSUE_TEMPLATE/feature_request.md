---
name: Feature request
about: Propose a new capability or improvement
labels: ["enhancement"]
---

## Problem to solve

<!-- What user-facing or operational problem does this address?
Features start from problems, not solutions. -->

## Proposed solution

<!-- Your idea. Rough is fine — architecture feedback happens in the thread. -->

## Which layer does it touch?

- [ ] `core/` — LLM client, budgets, resilience
- [ ] `tools/` — registry, executor, web tools, MCP
- [ ] `agents/` / `workflows/` — reasoning strategies
- [ ] `api/` — HTTP surface, streaming, caching
- [ ] `evaluation/` — quality harness
- [ ] `deploy/` / CI — infrastructure

## Production considerations

<!-- Reviewers will ask these — beat them to it: -->

- **Cost:** new LLM/tool calls per request? Estimated USD/1K requests?
- **Budget:** new loops or retries go through `core/budgets.py` (ADR-005)
- **Safety:** new outbound URLs go through `tools/ssrf_guard.py` (FM-08)
- **Fallback:** what happens when its dependencies are down?
- **Observability:** which metrics/alerts should exist if this ships?

## Alternatives considered

## Docs impact

- [ ] README feature list
- [ ] `docs/AGENT-CATALOG.md` row
- [ ] ADR needed (architecture change)
