# ADR-001: Layered module layout (agents / workflows / tools / core / api)

**Status:** Accepted · **Date:** 2026-10-16 · **Deciders:** architecture

## Context

The repo grew as a teaching artifact: modules mirror course chapters. As we
harden for production traffic, we must decide whether to restructure into a
`src/` package or keep the top-level layer packages.

## Decision

Keep five top-level layer packages with a strict dependency direction:

```
api → agents → workflows → tools → core
                agents → core
                api → core (types/exceptions only)
```

Rules enforced in review:

1. `core/` depends on nothing internal (only third-party).
2. `tools/` may import `core/` only.
3. `workflows/` may import `core/` and `tools/`.
4. `agents/` may import `core/`, `tools/`, `workflows/`.
5. `api/` may import everything but must contain no business logic.
6. No package imports from `api/` upward. No cycles, ever.

## Alternatives considered

- **Single `src/askweb/` package:** cleaner for PyPI publishing. Rejected
  for now — the course lineage is a feature (learners navigate by concept),
  and a mega-move would break every open PR and tutorial link. Revisit if
  the project publishes to PyPI.
- **Hexagonal / ports-and-adapters:** overkill for the size; our layer rule
  gives the same testability (mock at `core/` and `tools/` boundaries).

## Consequences

- Import direction doubles as the mocking strategy in tests: fake `LLMClient`
  and `BaseTool`, and everything above is unit-testable without network.
- New modules must state their layer in the PR template ("Impact Area").
- `tools/mcp_server.py` (inverted dependency: tools exposed OUT) is the one
  sanctioned exception — it exposes tools, it does not consume agents.
