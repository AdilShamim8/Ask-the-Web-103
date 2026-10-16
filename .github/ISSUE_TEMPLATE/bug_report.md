---
name: Bug report
about: Something broke or behaved unexpectedly
labels: ["bug", "triage"]
---

## What happened?

<!-- Clear description of the bug. Include the exact query / request if applicable. -->

## What did you expect?

## Environment

- Deployment: [ local / staging / production / not sure ]
- Version / image tag: [ e.g. v2.0.0, sha-abc1234 — from `/v1/health` ]
- Agent type: [ auto / react / reflexion / orchestrator ]

## Evidence

<!-- The single most useful thing you can attach: -->

- [ ] Request ID (from the `X-Request-ID` response header) — lets us trace the exact request
- [ ] Response body (redact anything sensitive)
- [ ] Screenshot (if UI)

```
paste request/response or logs here
```

## Error code

<!-- If the response included one of our stable error codes, check it: -->

- [ ] `budget_exceeded` — request hit its resource ceiling (working as designed? see ADR-005)
- [ ] `rate_limited` — throttled (by design)
- [ ] `llm_error` / `provider_unavailable`
- [ ] `search_error` / `scraping_error` / `ssrf_blocked`
- [ ] `tool_execution_error` / `tool_validation_error` / `tool_not_found`
- [ ] `max_iterations_exceeded` / `context_window_exceeded`
- [ ] other / not sure
