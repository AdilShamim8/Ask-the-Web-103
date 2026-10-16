# Contributing to Ask-the-Web

Thank you for improving the project! This document defines the bar for
merges. It exists so the codebase stays production-clean, not to gatekeep.

## Ground Rules

1. **One logical change per PR.** If you can describe it as two sentences
   starting with "and", split it.
2. **All commits are conventional**: `feat(scope): ...`, `fix(scope): ...`,
   `docs: ...`, `refactor: ...`, `test: ...`, `chore: ...`.
3. **No secrets, ever.** Use `.env.example` as the template; `.env` is
   git-ignored and CI will fail on any detected credential.
4. **Production code paths must be budgeted.** Any new LLM call, tool call,
   or loop must go through `core/budgets.py` — see ADR-005.
5. **New tools must be SSRF-safe.** Route all outbound HTTP through
   `tools/http_client.py` and validate URLs with `tools/ssrf_guard.py`.

## Development Setup

```bash
git clone https://github.com/AdilShamim8/Ask-the-Web-103.git
cd Ask-the-Web-103
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
cp .env.example .env   # add your keys
make test              # must pass before you push
```

## Before You Push

```bash
make lint        # ruff (style + imports) — zero warnings
make typecheck   # mypy strict
make test        # pytest with coverage gate (>= 70% on core/, tools/)
make compile     # python -m compileall sanity pass
```

CI runs the same four jobs on every PR — `ci.yml`. If it's red locally,
it will be red on GitHub.

## Pull Request Checklist

- [ ] Commits follow conventional format
- [ ] `make lint && make typecheck && make test` all green locally
- [ ] New behavior has tests (unit + one integration where relevant)
- [ ] New config has an entry in `.env.example` and `configs/settings.py`
- [ ] Docs updated: `README.md` feature list, `CHANGELOG.md` under
      `Unreleased`, ADR added if an architectural decision changed
- [ ] No new dependency without justification in the PR description
- [ ] Anything touching agent loops verified against budget exhaustion
      (test that a runaway loop returns `BudgetExceededError`, not a hang)

## Architecture Changes

Anything that moves a module boundary, changes the public API surface, or
alters scaling assumptions **requires an ADR** in
`docs/architecture/adr/`. Copy the nearest existing ADR as a template.
