<div align="center">

#  Project 3 - Build an "Ask-the-Web" Agent similar to Perplexity with Tool calling

### A production-grade, Perplexity-like AI research agent
### built with ReACT · ReWOO · Reflexion · Tree Search · MCP · A2A

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)
[![Anthropic](https://img.shields.io/badge/Anthropic-Claude-CC785C?style=for-the-badge)](https://anthropic.com)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Pytest-yellow?style=for-the-badge&logo=pytest)](https://pytest.org)

<br/>

> **Ask anything. The agent searches, reasons, verifies, and answers —**
> **with full citations, streaming output, and production-grade reliability.**
> ### To better understand this project, first visit this link for a visualization of the project and what I built: [Link](https://ask-the-web.space-z.ai/)
> ### Then, if you want to learn each topic in a tutorial format, read this file thoroughly: [Link](https://github.com/AdilShamim8/Ask-the-Web-103/blob/main/Tutorial-103.md)

<br/>

[Quick Start](#-quick-start) •
[Architecture](#-architecture) •
[Agents](#-agent-types) •
[API Reference](#-api-reference) •
[Configuration](#-configuration) •
[Evaluation](#-evaluation) •
[Contributing](#-contributing)

</div>

---

## Table of Contents

- [What Is This?](#-what-is-this)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Setup](#environment-setup)
  - [Running Locally](#running-locally)
  - [Running with Docker](#running-with-docker)
- [Agent Types](#-agent-types)
  - [ReACT Agent](#1-react-agent)
  - [Reflexion Agent](#2-reflexion-agent)
  - [ReWOO Agent](#3-rewoo-agent)
  - [Orchestrator Agent](#4-orchestrator-agent)
  - [Tree Search Agent](#5-tree-search-agent)
- [Workflows](#-workflows)
  - [Prompt Chaining](#prompt-chaining)
  - [Routing](#routing)
  - [Parallelization](#parallelization)
  - [Reflection](#reflection)
- [Tools](#-tools)
  - [Built-in Tools](#built-in-tools)
  - [MCP Integration](#mcp-integration)
  - [Adding Custom Tools](#adding-custom-tools)
- [Multi-Agent Systems](#-multi-agent-systems)
  - [Orchestrator-Worker](#orchestrator-worker-pattern)
  - [A2A Protocol](#a2a-agent-to-agent-protocol)
- [API Reference](#-api-reference)
  - [Endpoints](#endpoints)
  - [Request & Response Schemas](#request--response-schemas)
  - [Streaming (SSE)](#streaming-sse)
  - [Authentication](#authentication)
- [Configuration](#-configuration)
- [Evaluation](#-evaluation)
  - [Answer Quality Metrics](#answer-quality-metrics)
  - [Running Benchmarks](#running-benchmarks)
- [Observability](#-observability)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## What Is This?

**Ask-the-Web Agent** is a production-ready AI research assistant that works
like [Perplexity AI](https://perplexity.ai) — but fully open, self-hosted,
and extensible.

You ask a question in natural language. The agent:

1. **Plans** how to answer it (which strategy, how many steps)
2. **Searches** the web in real time using Tavily or SerpAPI
3. **Scrapes** relevant pages for detailed content
4. **Reasons** step-by-step using one of five agent strategies
5. **Verifies** its own answer through self-critique (Reflexion)
6. **Synthesizes** a final, cited, markdown-formatted answer
7. **Streams** the result token-by-token to the client

Unlike a raw LLM, this agent never makes up facts — every claim is
grounded in real-time web sources with inline citations.

### Why build this?

| Problem with raw LLMs | How this agent solves it |
|---|---|
| Knowledge cutoff (training data is stale) | Real-time web search on every query |
| Hallucination (confident but wrong) | Source-grounded answers + Reflexion critique |
| No citations (can't verify claims) | Every fact linked to a URL |
| Single-shot (one chance to get it right) | Multi-step reasoning with tool loops |
| Can't handle complex multi-part questions | Orchestrator decomposes and parallelizes |

---

## Key Features

###  Five Agent Strategies
Choose automatically via smart routing or manually per request:
- **ReACT** — Fast, iterative reason-and-act loops
- **Reflexion** — ReACT + self-critique and automatic revision
- **ReWOO** — Full plan upfront, parallel execution, single synthesis
- **Orchestrator** — Decomposes complex queries into parallel sub-agents
- **Tree Search** — Explores multiple reasoning paths, picks the best

###  Production Tool Stack
- **Web Search** — Tavily (primary) or SerpAPI (fallback)
- **Web Scraper** — Playwright + BeautifulSoup, cleans boilerplate
- **Calculator** — Safe sandboxed math expression evaluator
- **Summarizer** — Condenses long scraped content
- **MCP Support** — Connect any Model Context Protocol server

###  Multi-Agent Coordination
- **Orchestrator-Worker** — Spawn N parallel specialist agents
- **A2A Protocol** — Agent-to-Agent HTTP communication standard
- **MultiAgentCoordinator** — Route tasks to registered specialist agents

###  API & Streaming
- **REST API** — FastAPI with full OpenAPI docs
- **SSE Streaming** — Token-by-token answer delivery
- **Redis Cache** — SHA256-keyed response caching (1hr TTL)
- **Rate Limiting** — Per-IP sliding window

###  Evaluation System
- **LLM-as-Judge** — Multi-dimensional answer quality scoring
- **Text Metrics** — Citation coverage, structure, length (no LLM cost)
- **Benchmark Suite** — 5 built-in test cases across categories
- **Parallel Voting** — Majority-vote answer verification

###  Production Infrastructure
- **Structured logging** — structlog + rich, JSON in production
- **Prometheus metrics** — `/metrics` endpoint
- **Docker + Compose** — One-command deployment
- **Retry logic** — Tenacity-backed exponential backoff
- **Context management** — Automatic token trimming at window limits
- **Multi-provider** — Switch between OpenAI and Anthropic

---

##  Architecture

### System Overview

```
                        ┌─────────────────────────────────┐
                        │         Client (HTTP/SSE)        │
                        └──────────────┬──────────────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │         FastAPI (REST API)       │
                        │  middleware: rate limit, logging  │
                        │  middleware: request ID, errors   │
                        └──────────────┬──────────────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │          Redis Cache             │
                        │   (SHA256 keyed, 1hr TTL)        │
                        └──────────────┬──────────────────┘
                                  miss │
                        ┌─────────────▼───────────────────┐
                        │         Query Router             │
                        │  rule-based pre-filter +         │
                        │  LLM-based classification        │
                        └──┬───────┬──────┬──────┬────────┘
                           │       │      │      │
              ┌────────────▼─┐ ┌───▼──┐ ┌▼────┐ ┌▼──────────────┐
              │  ReACT Agent │ │ReWOO │ │Refl.│ │  Orchestrator │
              │  (fast Q&A)  │ │Agent │ │Agent│ │  (multi-part) │
              └──────┬───────┘ └──┬───┘ └──┬──┘ └──────┬────────┘
                     │            │         │            │
              ┌──────▼────────────▼─────────▼────────────▼───────┐
              │                 Tool Executor                      │
              │          (parallel or sequential)                  │
              └───┬──────────┬──────────┬──────────┬─────────────┘
                  │          │          │          │
           ┌──────▼──┐ ┌─────▼───┐ ┌───▼────┐ ┌──▼──────────┐
           │   Web   │ │  Web    │ │ Calc-  │ │     MCP     │
           │ Search  │ │ Scraper │ │ ulator │ │   Servers   │
           └─────────┘ └─────────┘ └────────┘ └─────────────┘
```

### Agent Decision Flow

```
User Query
    │
    ▼
┌───────────────────────────────────────────────┐
│              TaskPlanner                       │
│   Analyzes complexity → PlanningLevel (1-5)   │
└───────────────────────┬───────────────────────┘
                        │
          ┌─────────────▼──────────────┐
          │       QueryRouter          │
          │  Rule-based quick classify │
          │  ──────────────────────── │
          │  LLM-based deep classify   │
          └─────┬──────┬──────┬───────┘
                │      │      │
     ┌──────────▼─┐  ┌─▼────┐ ┌▼───────────────────┐
     │  simple_qa │  │ calc │ │  research /         │
     │  → ReACT   │  │→ReACT│ │  multi_faceted /    │
     └────────────┘  └──────┘ │  → Reflexion /      │
                               │  → Orchestrator     │
                               └─────────────────────┘
                                         │
                               ┌─────────▼──────────┐
                               │   ReACT Loop        │
                               │   ┌─────────────┐   │
                               │   │   THINK     │   │
                               │   │  (LLM call) │   │
                               │   └──────┬──────┘   │
                               │          │           │
                               │   ┌──────▼──────┐   │
                               │   │     ACT     │   │
                               │   │ (tool calls)│   │
                               │   └──────┬──────┘   │
                               │          │           │
                               │   ┌──────▼──────┐   │
                               │   │   OBSERVE   │   │
                               │   │  (results)  │   │
                               │   └──────┬──────┘   │
                               │          │           │
                               │     done?│ no → loop │
                               └──────────┼───────────┘
                                          │ yes
                               ┌──────────▼───────────┐
                               │    Final Answer       │
                               │  (with citations)     │
                               └──────────────────────┘
```

### Token & Context Management

```
Every LLM call:
    messages → TokenCounter.count_messages()
                        │
              exceeds context limit?
                   yes │          no
                        │           │
          trim_to_fit() │           │ → proceed
          (drop oldest  │
           non-system   │
           messages)    │
                        └──────────►│ → LLM call
```

---

## 📁 Project Structure

```
ask_the_web_agent/
│
├── 📄 pyproject.toml              # Dependencies, build config, tool settings
├── 📄 .env.example                # All environment variables documented
├── 📄 docker-compose.yml          # Agent + Redis + Prometheus
├── 📄 Dockerfile                  # Multi-stage build (builder + runtime)
├── 📄 README.md                   # This file
│
├── 📁 configs/                    # Application configuration
│   ├── settings.py                # Pydantic Settings (type-safe env loading)
│   ├── logging_config.py          # structlog + rich setup
│   └── prometheus.yml             # Prometheus scrape config
│
├── 📁 core/                       # Shared infrastructure
│   ├── exceptions.py              # Full exception hierarchy
│   ├── message_types.py           # Message, ToolCall, AgentState types
│   ├── token_counter.py           # tiktoken-based counter + trim
│   └── llm_client.py              # Unified OpenAI + Anthropic client
│
├── 📁 tools/                      # Tool layer
│   ├── base_tool.py               # BaseTool ABC + ToolDefinition schema
│   ├── tool_registry.py           # Central tool store
│   ├── tool_executor.py           # Parallel + sequential execution
│   ├── web_search.py              # Tavily / SerpAPI search
│   ├── web_scraper.py             # httpx + BeautifulSoup scraper
│   ├── calculator.py              # Safe sandboxed math eval
│   ├── summarizer.py              # Extractive text summarizer
│   └── mcp_client.py              # MCP protocol client + registry
│
├── 📁 agents/                     # Agent implementations
│   ├── base_agent.py              # Abstract base + shared utilities
│   ├── react_agent.py             # ReACT: iterative reason-act-observe
│   ├── reflexion_agent.py         # Reflexion: ReACT + self-critique
│   ├── rewoo_agent.py             # ReWOO: plan-execute-solve
│   ├── orchestrator.py            # Orchestrator-Worker: decompose + parallel
│   ├── tree_search_agent.py       # Best-first tree search
│   ├── planner.py                 # Task planner + PlanningLevel
│   └── a2a.py                     # Agent-to-Agent protocol
│
├── 📁 workflows/                  # Workflow patterns
│   ├── prompt_chaining.py         # Sequential chained LLM calls
│   ├── routing.py                 # LLM + rule-based query router
│   ├── parallelization.py         # Sectioning + voting patterns
│   ├── reflection.py              # Standalone critique-revise loop
│   └── __init__.py                # build_routed_pipeline()
│
├── 📁 evaluation/                 # Quality assessment
│   ├── metrics.py                 # Fast rule-based text metrics
│   ├── evaluator.py               # LLM-as-judge evaluator
│   └── benchmarks.py              # Benchmark runner + built-in cases
│
├── 📁 api/                        # FastAPI application
│   ├── main.py                    # App factory + lifespan
│   ├── routes.py                  # All endpoint handlers
│   ├── schemas.py                 # Pydantic request/response models
│   ├── middleware.py              # Rate limit, logging, error handling
│   └── cache.py                   # Redis response cache
│
└── 📁 tests/                      # Full test suite
    ├── test_tools.py              # Tool unit tests
    ├── test_agents.py             # Agent behavior tests
    ├── test_workflows.py          # Workflow + metric tests
    └── test_api.py                # API endpoint + middleware tests
```

---

##  Quick Start

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Uses `match` statements, `Self` type |
| Redis | 7+ | For response caching |
| Docker | 24+ | Optional, for containerized run |
| OpenAI API Key | — | Primary LLM provider |
| Tavily API Key | — | Primary search provider |

> **Minimum to get started:** Python 3.11 + OpenAI key + Tavily key.
> Redis and Docker are optional for local development.

---

### Installation

#### Option A — pip (development)

```bash
# 1. Clone the repository
git https://github.com/AdilShamim8/Ask-the-Web-103.git
cd ask-the-web-agent

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install with all dev dependencies
pip install -e ".[dev]"

# 4. Install Playwright browser (for web scraping)
playwright install chromium

# 5. Verify installation
python -c "import openai, fastapi, redis; print('✅ All dependencies OK')"
```

#### Option B — Docker (production)

```bash
git clone https://github.com/AdilShamim8/Ask-the-Web-103.git
cd ask-the-web-agent
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
```

---

### Environment Setup

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

Open `.env` and set the required values:

```env
# ── REQUIRED ────────────────────────────────────────────────────────────────

# LLM provider (at least one required)
OPENAI_API_KEY=sk-proj-...          # Get at: https://platform.openai.com
ANTHROPIC_API_KEY=sk-ant-...        # Get at: https://console.anthropic.com

# Search provider (at least one required)
TAVILY_API_KEY=tvly-...             # Get at: https://tavily.com (free tier available)
SERPAPI_API_KEY=...                 # Get at: https://serpapi.com (fallback)

# ── OPTIONAL ────────────────────────────────────────────────────────────────

# Which providers to use by default
DEFAULT_LLM_PROVIDER=openai         # openai | anthropic
DEFAULT_MODEL=gpt-4o                # gpt-4o | gpt-4o-mini | claude-3-5-sonnet-...
SEARCH_PROVIDER=tavily              # tavily | serpapi

# Redis (skip for local dev — cache silently disabled if unavailable)
REDIS_URL=redis://localhost:6379/0

# Agent behavior
MAX_AGENT_ITERATIONS=10             # Hard cap on reasoning loops
MAX_TOKENS_PER_RESPONSE=4096        # Max tokens in any single LLM response
CONTEXT_WINDOW_LIMIT=120000         # Trim history above this token count

# Application
APP_ENV=development                 # development | staging | production
LOG_LEVEL=INFO                      # DEBUG | INFO | WARNING | ERROR

# Rate limiting
RATE_LIMIT_REQUESTS=100             # Requests per window per IP
RATE_LIMIT_WINDOW=60                # Window size in seconds

# Timeouts (seconds)
LLM_TIMEOUT=60.0
SEARCH_TIMEOUT=15.0
SCRAPE_TIMEOUT=20.0
```

> **Security note:** Never commit `.env` to version control.
> The `.gitignore` already excludes it.

---

### Running Locally

```bash
# Start Redis (required for caching — skip if you don't need it)
docker run -d -p 6379:6379 redis:7-alpine

# Start the API server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Verify it's running
curl http://localhost:8000/v1/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "providers": {
    "openai": true
  }
}
```

Open the interactive API docs:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

> **Note:** Docs are disabled in production (`APP_ENV=production`).

---

### Running with Docker

```bash
# Start everything: agent + Redis + Prometheus
docker-compose up -d

# View logs
docker-compose logs -f agent

# Scale workers (behind a load balancer)
docker-compose up -d --scale agent=3

# Stop everything
docker-compose down

# Stop and remove volumes (wipes Redis data)
docker-compose down -v
```

Services started by `docker-compose up`:

| Service | Port | Description |
|---|---|---|
| `agent` | `8000` | FastAPI application |
| `redis` | `6379` | Response cache |
| `prometheus` | `9090` | Metrics collection |

---

## Agent Types

The system supports five distinct agent strategies. The `auto` mode
uses the smart router to pick the right one automatically.

### 1. ReACT Agent

**Best for:** Simple factual questions, current events, quick lookups.

**How it works:**

```
THINK → ACT → OBSERVE → THINK → ACT → OBSERVE → ... → FINAL ANSWER
```

The LLM alternates between reasoning about what to do next (THINK)
and calling tools (ACT), then observing the tool results (OBSERVE).
This continues until the LLM produces a response with no tool calls.

**Example interaction:**

```
User:  "Who won the 2024 Nobel Prize in Physics?"

Agent THINKS: I need to search for this.
Agent ACTS:   web_search("2024 Nobel Prize Physics winner")
Agent OBSERVES: [Search results: John Hopfield and Geoffrey Hinton...]
Agent THINKS: I have the answer.
Agent ANSWERS: "The 2024 Nobel Prize in Physics was awarded to
               John Hopfield and Geoffrey Hinton..."
```

**Configuration:**
```json
{
  "query": "Who won the 2024 Nobel Prize in Physics?",
  "agent_type": "react",
  "max_iterations": 5
}
```

**Token cost:** Low (2 LLM calls per tool use)
**Latency:** Fast (2–4 seconds typical)

---

### 2. Reflexion Agent

**Best for:** Research questions requiring accuracy verification,
complex topics where errors are costly.

**How it works:**

```
ReACT run → Initial Answer
    │
    ▼
Reflection LLM: "Is this answer accurate and complete?"
    │
    ├── VERDICT: ACCEPT → Return answer
    │
    └── VERDICT: REVISE → ReACT run with critique context
                              │
                              ▼
                         Revised Answer → Reflect again (max N rounds)
```

The agent critiques its own answer using a separate LLM call that
checks for factual accuracy, completeness, and citation quality.

**Example critique output:**
```
VERDICT: REVISE
CRITIQUE: The answer states the prize was awarded for "AI research"
          but does not specify the cited contribution (artificial neural
          networks and Boltzmann machines).
SUGGESTION: Search for the specific scientific contribution cited by
            the Nobel Committee and include it in the answer.
```

**Configuration:**
```json
{
  "query": "Explain the mechanism behind CRISPR-Cas9 gene editing",
  "agent_type": "reflexion"
}
```

**Token cost:** Medium (adds 1–2 LLM calls per reflection round)
**Latency:** Medium (5–12 seconds typical)

---

### 3. ReWOO Agent

**Best for:** Queries with a clear, known sequence of research steps.
Most token-efficient for multi-step research.

**How it works (Xu et al., 2023):**

```
Phase 1 — PLAN  (1 LLM call):
    Step 1: Thought: ... Tool: web_search  Args: {...}
    Step 2: Thought: ... Tool: scrape_webpage Args: {url: #E1.results[0].url}
    Step 3: Thought: ... Tool: web_search  Args: {...}

Phase 2 — EXECUTE (parallel where possible):
    Steps without #E refs → run in PARALLEL
    Steps with #E refs    → run SEQUENTIALLY after dependencies

Phase 3 — SOLVE (1 LLM call):
    LLM reads all observations → writes final answer
```

**Why it's efficient:** Instead of O(2N) LLM calls (ReACT), ReWOO
uses O(2) LLM calls regardless of how many tool steps are needed.

**Example plan generated:**
```
Step 1:
Thought: Search for recent SpaceX launches
Tool: web_search
Args: {"query": "SpaceX Starship launches 2024", "num_results": 5}

Step 2:
Thought: Get detailed info from the most relevant result
Tool: scrape_webpage
Args: {"url": "#E1"}

Step 3:
Thought: Search for launch success metrics
Tool: web_search
Args: {"query": "SpaceX Starship 2024 success rate statistics"}
```

**Configuration:**
```json
{
  "query": "What were SpaceX's key milestones in 2024?",
  "agent_type": "rewoo"
}
```

**Token cost:** Lowest for multi-step (only 2 LLM calls total)
**Latency:** Fast (parallel execution)

---

### 4. Orchestrator Agent

**Best for:** Complex multi-part questions that span multiple
independent topics, comparison queries, comprehensive research reports.

**How it works:**

```
Orchestrator LLM: Decompose into sub-questions
    │
    ├── "Sub-question 1" → Worker ReACT Agent 1 ─┐
    ├── "Sub-question 2" → Worker ReACT Agent 2 ─┤ (parallel)
    ├── "Sub-question 3" → Worker ReACT Agent 3 ─┤
    └── "Sub-question N" → Worker ReACT Agent N ─┘
                                                   │
                                    ┌──────────────▼──────────────┐
                                    │   Orchestrator LLM          │
                                    │   Synthesizes all answers   │
                                    │   into unified response     │
                                    └─────────────────────────────┘
```

**Example decomposition:**

Query: *"Compare the AI strategies of the US, China, and EU in 2024"*

```json
[
  "What is the United States AI strategy and major initiatives in 2024?",
  "What is China's AI development strategy and investments in 2024?",
  "What is the European Union's AI regulatory and investment approach in 2024?"
]
```

All three sub-questions are answered simultaneously by parallel
ReACT agents, then synthesized into a unified comparison.

**Configuration:**
```json
{
  "query": "Compare AI chip strategies of NVIDIA, AMD, and Intel in 2024",
  "agent_type": "orchestrator"
}
```

**Token cost:** Higher (N parallel agents + synthesis call)
**Latency:** Moderate despite N agents (they run in parallel)

---

### 5. Tree Search Agent

**Best for:** Ambiguous questions with multiple valid approaches,
exploratory research, hypothesis generation and testing.

**How it works (Beam Search over reasoning paths):**

```
Depth 0:  [Root: "Start researching..."]
              │
              ├── Expand: K=3 candidate thoughts
              │
Depth 1:  [Candidate A: 0.85]  [Candidate B: 0.72]  [Candidate C: 0.41]
              │                      │
              │ beam=2: keep top 2   │
              ▼                      ▼
Depth 2:  [A1: 0.91]  [A2: 0.78]  [B1: 0.89]  [B2: 0.55]
              │
              │ Terminal detected (score 0.91)
              ▼
         FINAL ANSWER from best terminal node
```

At each depth:
1. Each beam node generates `branching_factor` candidate next thoughts
2. All candidates are scored in parallel (0.0–1.0)
3. Top `beam_width` candidates become the next beam
4. If any candidate signals a final answer, the highest-scored wins

**Configuration:**
```json
{
  "query": "What might cause a sudden drop in transformer model performance?",
  "agent_type": "tree_search"
}
```

**Token cost:** Highest (branching factor × depth × 2 LLM calls)
**Latency:** Slower (but finds better answers for hard problems)

---

### Agent Selection Guide

```
                    Is the question simple and factual?
                              │
                    YES ──────┤──────── NO
                              │              │
                         [ ReACT ]      Does it have multiple
                                        independent sub-parts?
                                              │
                                    YES ──────┤──────── NO
                                              │              │
                                       [Orchestrator]   Is accuracy
                                                        critical?
                                                              │
                                                    YES ──────┤─── NO
                                                              │         │
                                                        [Reflexion] Is the
                                                                    sequence
                                                                    known?
                                                                        │
                                                               YES ─────┤── NO
                                                                        │        │
                                                                   [ ReWOO ] [TreeSearch]
```

Or just use `"agent_type": "auto"` and let the router decide.

---

## Workflows

Workflows are reusable reasoning patterns that agents are built from.
You can use them directly or compose them into custom agents.

### Prompt Chaining

Execute a sequence of LLM calls where each step's output feeds the next.

```python
from workflows.prompt_chaining import PromptChain, ChainStep
from core.llm_client import LLMClient

chain = PromptChain(llm_client=LLMClient())

chain.add_step(ChainStep(
    name="identify_intent",
    prompt_template="Analyze this question: {query}\nIdentify: intent, entities, time-sensitivity.",
    output_key="intent",
))

chain.add_step(ChainStep(
    name="generate_queries",
    prompt_template="Generate 3 search queries for:\nQuestion: {query}\nIntent: {intent}",
    output_key="search_queries",
    transform=lambda text: text.strip().split("\n"),  # parse into list
))

result = await chain.run({"query": "Latest AI breakthroughs 2024"})
print(result["search_queries"])
# → ["AI breakthroughs 2024", "machine learning advances 2024", ...]
```

### Routing

Route queries to different handlers based on LLM or rule-based classification.

```python
from workflows.routing import QueryRouter, QueryClassifier, Route

# Rule-based (free, no LLM call)
route = QueryClassifier.quick_classify("hello there")
# → "conversational"

# LLM-based
router = QueryRouter(llm_client=llm)
router.add_route(Route("simple_qa", "Short factual Q&A", react_handler))
router.add_route(Route("research", "Deep analysis needed", reflexion_handler))

route_name, result = await router.route("What causes inflation?")
```

### Parallelization

**Sectioning** — Run the same worker on multiple items concurrently:

```python
from workflows.parallelization import ParallelSectioning

sectioner = ParallelSectioning(max_concurrency=5)

urls = ["https://a.com", "https://b.com", "https://c.com"]
results = await sectioner.run(urls, worker=scrape_tool.execute)
```

**Voting** — Run the same prompt N times, take majority vote:

```python
from workflows.parallelization import ParallelVoting, AnswerVerifier

voter = ParallelVoting(llm_client=llm, num_votes=5, temperature=0.7)
majority, distribution = await voter.vote(messages, extract_answer=str.strip)

# Fact verification
verifier = AnswerVerifier(llm_client=llm, num_votes=3)
result = await verifier.verify(
    claim="The Eiffel Tower is 330 meters tall",
    context=scraped_page_content,
)
# → {"verdict": "FALSE", "confidence": 0.85, "distribution": {...}}
```

### Reflection

Apply critique-and-revise to any generated text:

```python
from workflows.reflection import ReflectionWorkflow

reflector = ReflectionWorkflow(llm_client=llm, rounds=2)
result = await reflector.run(
    question="What is quantum entanglement?",
    initial_answer=draft_answer,
)
print(result["final_answer"])     # improved version
print(result["rounds"])           # list of {critique, revised_answer}
```

---

## Tools

### Built-in Tools

| Tool | Name | Description | Key Args |
|---|---|---|---|
| Web Search | `web_search` | Search via Tavily or SerpAPI | `query`, `num_results`, `search_depth` |
| Web Scraper | `scrape_webpage` | Fetch + clean page text | `url`, `extract_links` |
| Calculator | `calculator` | Safe math expression eval | `expression` |
| Summarizer | `summarize_text` | Extractive text summary | `text`, `max_sentences` |

### MCP Integration

Connect any [Model Context Protocol](https://modelcontextprotocol.io/) server:

```python
from tools.mcp_client import MCPRegistry, MCPServerConfig
from tools import build_default_registry

# Define your MCP servers
mcp = MCPRegistry()
mcp.add_server(MCPServerConfig(
    name="filesystem",
    base_url="http://localhost:3001",
    api_key="your-mcp-key",
))
mcp.add_server(MCPServerConfig(
    name="database",
    base_url="http://localhost:3002",
))

# Build registry: local tools + all MCP tools auto-discovered
base = build_default_registry()
registry = await mcp.build_registry(base_registry=base)

# Use with any agent
agent = build_agent(AgentType.REACT, registry=registry)
state = await agent.run("Query the database for last month's sales")
```

MCP tools are automatically discovered via the `tools/list` JSON-RPC call
and wrapped as standard `BaseTool` instances — the agent treats them
identically to built-in tools.

### Adding Custom Tools

Create any tool by subclassing `BaseTool`:

```python
from tools.base_tool import BaseTool, ToolDefinition
from core.exceptions import ToolExecutionError

class WeatherTool(BaseTool):
    """Fetch current weather for a city."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_weather",
            description="Get current weather conditions for any city.",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'Tokyo'",
                    },
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "default": "celsius",
                    },
                },
                "required": ["city"],
            },
        )

    async def execute(self, city: str, units: str = "celsius", **_) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.weather.example.com/current",
                params={"city": city, "units": units},
            )
        data = resp.json()
        return json.dumps(data)

# Register it
from tools import build_default_registry
registry = build_default_registry()
registry.register(WeatherTool())

# Use with any agent
agent = build_agent(AgentType.REACT, registry=registry)
```

**Requirements for a valid tool:**
1. Subclass `BaseTool`
2. Implement `definition` property → returns `ToolDefinition` with valid JSON Schema
3. Implement `async execute(**kwargs) -> str` → always returns a string
4. Raise `ToolExecutionError(tool_name, reason)` on failure (never raise raw exceptions)

---

## Multi-Agent Systems

### Orchestrator-Worker Pattern

The `OrchestratorAgent` implements the orchestrator-worker pattern natively.
One orchestrator LLM decomposes the query; N worker ReACT agents run in
parallel; the orchestrator synthesizes all results.

```python
from agents import AgentType, build_agent

agent = build_agent(
    agent_type=AgentType.ORCHESTRATOR,
    model="gpt-4o",
    max_workers=4,          # max parallel worker agents
    max_iterations=8,       # per-worker iteration cap
)

state = await agent.run(
    "Compare renewable energy adoption rates in Germany, France, and the UK"
)

print(state.final_answer)
print(state.metadata["sub_questions"])   # what the orchestrator decomposed
print(state.metadata["worker_iterations"])  # how many steps each worker took
```

### A2A (Agent-to-Agent) Protocol

Expose any agent as an A2A-compliant HTTP service, and call remote agents
from other agents using the standardized protocol.

**Expose your agent as an A2A server:**

```python
from agents.a2a import AgentCard, AgentCapability, create_a2a_router
from api.main import app

# Define what your agent can do
card = AgentCard(
    name="Research Specialist",
    description="Deep web research agent specializing in science topics",
    url="https://research-agent.yourdomain.com",
    capabilities=[
        AgentCapability(
            name="research",
            description="Research any scientific topic with citations",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )
    ],
)

# Define the handler
async def handle_task(capability: str, input_data: dict) -> dict:
    agent = build_agent(AgentType.REFLEXION)
    state = await agent.run(input_data["query"])
    return {
        "answer": state.final_answer,
        "sources": state.sources,
    }

# Mount A2A routes
a2a_router = create_a2a_router(card, handle_task)
app.include_router(a2a_router)
# Now serving:
#   GET  /.well-known/agent.json  → capability card
#   POST /a2a/tasks               → submit task
#   GET  /a2a/tasks/{id}          → poll status
#   DELETE /a2a/tasks/{id}        → cancel
```

**Call a remote agent from another agent:**

```python
from agents.a2a import A2AClient, AgentCard, MultiAgentCoordinator

# Discover remote agent
remote_card = AgentCard(
    name="Research Specialist",
    url="https://research-agent.yourdomain.com",
    description="...",
)

# Build coordinator
coordinator = MultiAgentCoordinator()
coordinator.register_agent(
    capability="research",
    client=A2AClient(remote_card, timeout=60.0),
)

# Delegate tasks
result = await coordinator.delegate(
    capability="research",
    input_data={"query": "Latest quantum computing breakthroughs"},
)

# Delegate multiple tasks in parallel
results = await coordinator.delegate_parallel([
    ("research", {"query": "US AI policy 2024"}),
    ("research", {"query": "EU AI Act implementation"}),
    ("research", {"query": "China AI investment 2024"}),
])
```

---

## 📡 API Reference

### Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| `GET` | `/v1/health` | Health check + provider status | None |
| `POST` | `/v1/ask` | Submit query (batch response) | Optional |
| `POST` | `/v1/ask/stream` | Submit query (SSE streaming) | Optional |
| `POST` | `/v1/evaluate` | Evaluate answer quality | Optional |
| `GET` | `/v1/models` | List available models | None |
| `GET` | `/metrics` | Prometheus metrics | None |

---

### Request & Response Schemas

#### `POST /v1/ask`

**Request:**
```json
{
  "query": "What are the latest breakthroughs in fusion energy?",
  "agent_type": "auto",
  "model": "gpt-4o",
  "max_iterations": 8,
  "stream": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `query` | `string` | required | Question (1–2000 chars) |
| `agent_type` | `enum` | `"auto"` | `auto` `react` `reflexion` `rewoo` `orchestrator` |
| `model` | `string` | env default | Override LLM model |
| `max_iterations` | `int` | env default | Max reasoning steps (1–20) |
| `stream` | `bool` | `false` | Enable SSE streaming |

**Response:**
```json
{
  "request_id": "a3f8b2c1d4e5",
  "query": "What are the latest breakthroughs in fusion energy?",
  "answer": "## Fusion Energy Breakthroughs in 2024\n\nSeveral significant...",
  "sources": [
    {
      "title": "NIF achieves fusion ignition milestone",
      "url": "https://www.science.org/..."
    }
  ],
  "agent_type": "react",
  "iterations": 3,
  "tools_called": ["web_search", "scrape_webpage"],
  "model": "gpt-4o",
  "cached": false,
  "metadata": {}
}
```

---

#### `POST /v1/evaluate`

**Request:**
```json
{
  "query": "What is the capital of France?",
  "answer": "## Answer\nThe capital of France is Paris.\n## Sources\n- https://example.com",
  "sources": [{"title": "Example", "url": "https://example.com"}],
  "ground_truth": "Paris"
}
```

**Response:**
```json
{
  "scores": {
    "factual_accuracy": 0.98,
    "completeness": 0.85,
    "clarity": 0.95,
    "source_usage": 0.90,
    "hallucination_risk": 0.97,
    "citation_coverage": 1.0,
    "length_score": 0.72,
    "structure_score": 0.70,
    "has_sources_section": 1.0
  },
  "feedback": {
    "factual_accuracy": "Claim is correct and well-supported.",
    "completeness": "Could include additional context about Paris.",
    "clarity": "Clear and concise.",
    "source_usage": "Source is cited correctly.",
    "hallucination_risk": "No hallucination detected."
  },
  "overall_score": 0.91,
  "passed": true
}
```

---

### Streaming (SSE)

The `/v1/ask/stream` endpoint uses
[Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events).
Each event is a JSON object.

**Event types:**

```
# 1. Metadata (sent first — before any tokens)
data: {"type": "metadata", "request_id": "abc", "sources": [...],
       "iterations": 3, "tools_called": ["web_search"]}

# 2. Token stream (one per token)
data: {"type": "token", "delta": "The ", "done": false}
data: {"type": "token", "delta": "answer ", "done": false}
data: {"type": "token", "delta": "is...", "done": false}

# 3. Completion signal
data: {"type": "done", "done": true}

# On error
data: {"type": "error", "error": "Search service unavailable"}
```

**Client example (JavaScript):**
```javascript
const source = new EventSource('/v1/ask/stream');
const response = await fetch('/v1/ask/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({query: 'What is quantum computing?'}),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const {done, value} = await reader.read();
  if (done) break;

  const lines = decoder.decode(value).split('\n');
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue;
    const event = JSON.parse(line.slice(6));

    if (event.type === 'token') process.stdout.write(event.delta);
    if (event.type === 'done') break;
    if (event.type === 'error') console.error(event.error);
  }
}
```

**Python client example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/v1/ask/stream",
        json={"query": "Latest AI news", "agent_type": "auto"},
    ) as resp:
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            import json
            event = json.loads(line[6:])
            if event["type"] == "token":
                print(event["delta"], end="", flush=True)
```

---

### Authentication

The API uses optional Bearer token authentication.
Set `API_KEY` in your `.env` to enable it:

```env
API_KEY=your-secret-key
```

Then include in requests:
```bash
curl -H "Authorization: Bearer your-secret-key" \
     -X POST http://localhost:8000/v1/ask \
     -d '{"query": "test"}'
```

If `API_KEY` is not set, all requests are allowed (development mode).

---

## Configuration

All settings are loaded from environment variables via Pydantic Settings.
Full reference:

| Variable | Type | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | `str` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | `str` | — | Anthropic API key |
| `DEFAULT_LLM_PROVIDER` | `openai\|anthropic` | `openai` | Primary LLM |
| `DEFAULT_MODEL` | `str` | `gpt-4o` | Default model name |
| `FALLBACK_MODEL` | `str` | `gpt-4o-mini` | Fallback on error |
| `TAVILY_API_KEY` | `str` | — | Tavily search key |
| `SERPAPI_API_KEY` | `str` | — | SerpAPI key (fallback) |
| `SEARCH_PROVIDER` | `tavily\|serpapi` | `tavily` | Search backend |
| `REDIS_URL` | `str` | `redis://localhost:6379/0` | Redis connection |
| `APP_ENV` | `development\|staging\|production` | `production` | Environment |
| `LOG_LEVEL` | `str` | `INFO` | Log verbosity |
| `MAX_AGENT_ITERATIONS` | `int` | `10` | Max reasoning loops |
| `MAX_TOKENS_PER_RESPONSE` | `int` | `4096` | Max response tokens |
| `CONTEXT_WINDOW_LIMIT` | `int` | `120000` | Token window cap |
| `RATE_LIMIT_REQUESTS` | `int` | `100` | Requests per window |
| `RATE_LIMIT_WINDOW` | `int` | `60` | Window size (seconds) |
| `LLM_TIMEOUT` | `float` | `60.0` | LLM request timeout |
| `SEARCH_TIMEOUT` | `float` | `15.0` | Search timeout |
| `SCRAPE_TIMEOUT` | `float` | `20.0` | Scrape timeout |

**Switching to Anthropic:**
```env
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-5-sonnet-20241022
```

**Using SerpAPI instead of Tavily:**
```env
SEARCH_PROVIDER=serpapi
SERPAPI_API_KEY=your-key
```

---

## Evaluation

### Answer Quality Metrics

Answers are evaluated on two levels:

**Level 1 — Rule-based (instant, free):**

| Metric | Description | Weight |
|---|---|---|
| `citation_coverage` | % of sources actually cited in answer | — |
| `length_score` | Penalizes too-short or too-long answers | — |
| `structure_score` | Presence of headers, lists, sections | — |
| `has_sources_section` | Answer ends with ## Sources | — |

**Level 2 — LLM-as-Judge (1 LLM call):**

| Metric | Description | Weight |
|---|---|---|
| `factual_accuracy` | Claims supported by sources | 30% |
| `completeness` | Fully addresses the question | 20% |
| `clarity` | Well-written and readable | 15% |
| `source_usage` | Citations correct and relevant | 15% |
| `hallucination_risk` | Grounded in evidence | 20% |

**Pass threshold:** Overall score ≥ 0.70

---

### Running Benchmarks

**Programmatic:**
```python
import asyncio
from evaluation.benchmarks import BenchmarkRunner, BenchmarkCase
from agents import AgentType

# Run built-in benchmark suite
runner = BenchmarkRunner(
    agent_type=AgentType.REACT,
    model="gpt-4o-mini",   # use cheaper model for benchmarks
)
results = asyncio.run(runner.run_all(concurrency=2))

print(f"Pass rate:   {results['pass_rate']:.0%}")
print(f"Avg score:   {results['avg_score']:.3f}")
print(f"Avg latency: {results['avg_latency_s']:.1f}s")
print(f"By category: {results['category_scores']}")
```

**Custom benchmark cases:**
```python
custom_cases = [
    BenchmarkCase(
        id="my_test_01",
        query="What is the latest version of Python?",
        expected_keywords=["3.12", "3.13", "python"],
        category="factual",
    ),
    BenchmarkCase(
        id="my_test_02",
        query="Explain the difference between RAG and fine-tuning",
        ground_truth="RAG retrieves context at inference time; fine-tuning updates weights",
        expected_keywords=["retrieval", "fine-tuning", "weights"],
        category="research",
    ),
]

results = asyncio.run(runner.run_all(cases=custom_cases))
```

**Expected benchmark output:**
```
╭─────────────────────────────────────────────────────╮
│              Benchmark Results Summary               │
├─────────────────────────────────────────────────────┤
│  Total cases:    5                                   │
│  Passed:         4  (80%)                            │
│  Avg score:      0.812                               │
│  Avg latency:    4.3s                                │
├─────────────────────────────────────────────────────┤
│  By category:                                        │
│    factual:        0.891                             │
│    research:       0.823                             │
│    calculation:    0.950                             │
│    multi_faceted:  0.754                             │
│    current_events: 0.742                             │
╰─────────────────────────────────────────────────────╯
```

---

## Observability

### Structured Logging

In development, logs are human-readable rich text:
```
2024-01-15 10:23:41 [info     ] react_agent.start    agent=ReACT query=What is the capital of France?
2024-01-15 10:23:41 [info     ] tool.execute.start   tool=web_search call_id=call_a3f8b
2024-01-15 10:23:42 [info     ] tool.execute.success tool=web_search elapsed_s=0.823
2024-01-15 10:23:43 [info     ] agent.completed      iterations=2 tools_called=1 elapsed_s=2.1
```

In production (`APP_ENV=production`), logs are JSON:
```json
{"event": "react_agent.start", "agent": "ReACT", "query": "...", "timestamp": "..."}
```

### Prometheus Metrics

Metrics are exposed at `/metrics` in Prometheus format:

```bash
curl http://localhost:8000/metrics
```

Key metrics to monitor:

| Metric | Type | Description |
|---|---|---|
| `http_requests_total` | Counter | Total requests by path + status |
| `http_request_duration_seconds` | Histogram | Request latency |
| `agent_iterations_total` | Counter | Reasoning iterations |
| `tool_calls_total` | Counter | Tool usage by name |
| `cache_hits_total` | Counter | Redis cache hit rate |

**Grafana dashboard** (import from `configs/grafana-dashboard.json`):

```
┌─────────────────────────────────────────────────────────────┐
│  Requests/min    │  P95 Latency   │  Cache Hit Rate         │
│      142         │    3.2s        │      67%                │
├─────────────────────────────────────────────────────────────┤
│  Agent Type Distribution    │  Tool Usage                   │
│  react        64%           │  web_search     78%           │
│  orchestrator 21%           │  scrape_webpage 18%           │
│  reflexion    15%           │  calculator      4%           │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing

### Run the Full Test Suite

```bash
# All tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Specific test file
pytest tests/test_agents.py -v

# Specific test class
pytest tests/test_agents.py::TestReACTAgent -v

# Specific test
pytest tests/test_agents.py::TestReACTAgent::test_direct_answer_no_tools -v

# Run only fast tests (skip integration)
pytest tests/ -v -m "not integration"
```

### Test Categories

| File | What it tests | Type |
|---|---|---|
| `test_tools.py` | Calculator, scraper, search, registry, executor | Unit |
| `test_agents.py` | ReACT, Reflexion, Orchestrator behavior + edge cases | Unit |
| `test_workflows.py` | Chaining, routing, voting, reflection, metrics | Unit |
| `test_api.py` | All endpoints, caching, middleware, error handling | Integration |

### Coverage Requirements

```bash
# Enforce 80% minimum coverage
pytest --cov=. --cov-fail-under=80
```

### Mocking Strategy

All tests mock the LLM client and HTTP calls — no real API keys needed:

```python
# Example: testing an agent without real LLM calls
from unittest.mock import AsyncMock, MagicMock
from core.llm_client import LLMClient

llm = MagicMock(spec=LLMClient)
llm.complete = AsyncMock(return_value=Message(
    role=Role.ASSISTANT,
    content="Mocked answer",
))

agent = ReACTAgent(llm_client=llm, registry=registry, executor=executor)
state = await agent.run("test query")
assert state.final_answer == "Mocked answer"
```

---

## Deployment

### Production Checklist

```
Before deploying to production:
  ☐ Set APP_ENV=production
  ☐ Set strong API_KEY (if using auth)
  ☐ Configure Redis with persistence (appendonly yes)
  ☐ Set MAX_AGENT_ITERATIONS to a safe limit (8-10)
  ☐ Configure RATE_LIMIT_REQUESTS appropriately
  ☐ Disable Swagger docs (automatic in production)
  ☐ Set up log aggregation (ELK, Datadog, etc.)
  ☐ Configure Prometheus + Grafana dashboards
  ☐ Set up health check monitoring
  ☐ Test /v1/health endpoint returns "ok"
```

### Docker Production Deploy

```bash
# Build production image
docker build --target runtime -t ask-web-agent:v1.0.0 .

# Run with environment file
docker run -d \
  --name ask-web-agent \
  --env-file .env.production \
  -p 8000:8000 \
  --restart unless-stopped \
  --memory 2g \
  --cpus 2 \
  ask-web-agent:v1.0.0
```

### Gunicorn (Multi-Worker)

For high-throughput production use:

```bash
gunicorn api.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keep-alive 5 \
  --log-level info
```

> **Worker count rule of thumb:** `2 × CPU cores + 1`
> For async workloads like this, 2–4 workers is usually optimal.

### Kubernetes (Helm-style manifest)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ask-web-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ask-web-agent
  template:
    metadata:
      labels:
        app: ask-web-agent
    spec:
      containers:
      - name: agent
        image: yourregistry/ask-web-agent:v1.0.0
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: ask-web-agent-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /v1/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

## Roadmap

### v1.1 — Near-term
- [ ] **Persistent memory** — Cross-session conversation history via Redis
- [ ] **Image understanding** — Multimodal support for vision queries
- [ ] **PDF/document ingestion** — Upload and query documents directly
- [ ] **Webhook callbacks** — POST result to URL when async job completes

### v1.2 — Medium-term
- [ ] **Fine-tuning pipeline** — Use benchmark results to fine-tune smaller models
- [ ] **Vector store integration** — RAG over your own knowledge base
- [ ] **Agent marketplace** — Plug-and-play specialist agents via A2A
- [ ] **Cost tracking** — Per-request token cost logging and budgets

### v2.0 — Long-term
- [ ] **Self-improving agents** — Agents that update their own system prompts
- [ ] **Multi-modal tools** — Image search, chart reading, video transcription
- [ ] **Federated agents** — Cross-organization A2A agent networks
- [ ] **On-device models** — Local Ollama/llama.cpp backend support

---

## Contributing

Contributions are welcome! Please read this section before submitting.

### Development Setup

```bash
git clone https://github.com/yourorg/ask-the-web-agent.git
cd ask-the-web-agent
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

### Pre-commit Hooks

```bash
# Runs automatically on git commit:
# - ruff (linting + formatting)
# - mypy (type checking)
# - pytest (fast unit tests only)
pre-commit run --all-files
```

### Pull Request Guidelines

1. **Fork** the repository and create a feature branch
   ```bash
   git checkout -b feature/my-new-agent
   ```

2. **Write tests first** — all new features need test coverage ≥ 80%

3. **Follow the patterns** — new agents extend `BaseAgent`,
   new tools extend `BaseTool`

4. **Type everything** — all functions must have complete type annotations

5. **Update docs** — add your feature to this README

6. **Pass CI:**
   ```bash
   ruff check .
   mypy .
   pytest tests/ --cov=. --cov-fail-under=80
   ```

7. Open a PR with:
   - Clear description of what and why
   - Example input/output
   - Performance impact (latency, token cost)

### Adding a New Agent

```python
# 1. Create agents/my_agent.py
class MyAgent(BaseAgent):
    async def run(self, query: str, **kwargs: Any) -> AgentState:
        ...  # implement your strategy

# 2. Register in agents/__init__.py
class AgentType(str, Enum):
    MY_AGENT = "my_agent"    # add this

agent_map[AgentType.MY_AGENT] = MyAgent  # add this

# 3. Add tests in tests/test_agents.py
class TestMyAgent:
    async def test_basic_run(self) -> None: ...

# 4. Document in README under "Agent Types"
```

---
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

- Website: [Adil Shamim](https://adilshamim.me/)
- GitHub: [Adil Shamim](https://github.com/AdilShamim8)
- Create an issue in this repository for questions or suggestions

---

<p align="center">
  <a href="https://github.com/AdilShamim8">
    <img src="https://img.shields.io/badge/GitHub-AdilShamim8-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Profile"/>
  </a>
  <span style="opacity:.6">&nbsp;</span>

  <a href="https://www.linkedin.com/in/adilshamim8">
    <img src="https://img.shields.io/badge/LinkedIn-AdilShamim8-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn Profile"/>
  </a>
  <span style="opacity:.6">&nbsp;</span>

  <a href="https://www.kaggle.com/adilshamim8">
    <img src="https://img.shields.io/badge/Kaggle-AdilShamim8-20BEFF?style=for-the-badge&logo=kaggle&logoColor=white" alt="Kaggle Profile"/>
  </a>
  <span style="opacity:.6">&nbsp;</span>

  <a href="https://x.com/adil_shamim8">
    <img src="https://img.shields.io/badge/Twitter%2FX-@adil__shamim8-000000?style=for-the-badge&logo=x&logoColor=white" alt="Twitter/X Profile"/>
  </a>
  <span style="opacity:.6">&nbsp;</span>

  <a href="https://adilshamim8.medium.com/">
    <img src="https://img.shields.io/badge/Medium-AdilShamim8-12100E?style=for-the-badge&logo=medium&logoColor=white" alt="Medium Profile"/>
  </a>
</p>
<div align="center">
  
⭐ **If you find this repository helpful, please consider giving it a star!** ⭐

</div>
