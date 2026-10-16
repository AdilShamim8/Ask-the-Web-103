# ADR-004: MCP for tool extension, A2A for agent federation

**Status:** Accepted · **Date:** 2026-10-16

## Context

The project implements both Anthropic's **MCP** (Model Context Protocol —
standardized tool discovery and invocation) and Google's **A2A**
(Agent-to-Agent — agent cards, task lifecycle, remote delegation). Both
solve "call external capabilities," and a production decision must say
which one to use where — otherwise teams will build the same integration
twice, in two protocols, with two failure stories.

## Decision

Use **MCP as the tool boundary** and **A2A as the agent boundary**:

| Concern | Protocol | Why |
| ------- | -------- | ----- |
| Add a search / DB / file tool to the registry | MCP (`tools/mcp_client.py`, `tools/mcp_server.py`) | Tool-calling is synchronous, schema-shaped, cheap; MCP's `tools/list` → `tools/call` flow maps 1:1 to our `BaseTool` |
| Delegate a whole sub-question to a remote specialized agent | A2A (`agents/a2a*.py`) | Tasks are long-running, stateful, and need a lifecycle (submitted → working → completed) plus capability discovery via AgentCard |

Boundaries in code:

1. MCP-discovered tools wrap into `BaseTool` and enter the normal
   `ToolRegistry` — the executor's guards (SSRF, timeouts, budgets,
   truncation) apply automatically. An MCP server cannot opt out.
2. A2A task stores are Redis-backed with TTL + max-delivery + DLQ semantics
   (FM-12); the old in-memory dict store was a restart-away data loss.
3. Every remote A2A agent sits behind a per-agent circuit breaker; a dead
   specialist degrades that capability, not the orchestrator (FM-13).
4. Capability selection is explicit: the planner assigns `assigned_agent`
   from the A2A registry's AgentCards — no implicit magic discovery at
   request time.

## Alternatives considered

- **A2A only** (wrap every tool as a remote agent): rejected — tool calls
  are 100× cheaper than task round-trips; the overhead would dominate.
- **MCP only** (wrap remote agents as tools): rejected — loses task
  lifecycle, long-polling semantics, and multi-agent status visibility.
- **Custom internal protocol:** rejected — both standards have ecosystem
  tooling; NIH protocols don't.

## Consequences

- Two protocols is conscious scope; each stays in its module and neither
  leaks into `api/`.
- Protocol version pinning: MCP `2024-11-05` initialize handshake; A2A
  agent cards versioned; compatibility checked at registration, with a
  startup warning on mismatch (not a hard fail — partial degradation).
