from __future__ import annotations

"""
Planning Autonomy Module

Implements explicit task planning as a separate reasoning layer.
The planner decides WHAT to do; agents decide HOW to do it.

Levels of planning autonomy:
    L1 — No planning:     Direct LLM response
    L2 — Reactive:        ReACT (plan one step at a time)
    L3 — Batch planning:  ReWOO (full plan upfront)
    L4 — Hierarchical:    Tasks broken into sub-plans recursively
    L5 — Self-directing:  Agent modifies its own plan mid-execution
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import structlog

from core.llm_client import LLMClient
from core.message_types import Message, Role

logger = structlog.get_logger(__name__)


class PlanningLevel(IntEnum):
    NONE        = 1   # Direct LLM answer
    REACTIVE    = 2   # ReACT: one step at a time
    BATCH       = 3   # ReWOO: full plan upfront
    HIERARCHICAL= 4   # Plans with sub-plans
    SELF_MODIFY = 5   # Can revise plan mid-execution


@dataclass
class TaskSpec:
    """A single task in a hierarchical plan."""
    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    sub_tasks: list["TaskSpec"] = field(default_factory=list)
    assigned_agent: str = "react"
    estimated_complexity: int = 1   # 1-5 scale
    status: str = "pending"         # pending, running, done, failed


@dataclass
class ExecutionPlan:
    """Full hierarchical execution plan for a query."""
    query: str
    planning_level: PlanningLevel
    tasks: list[TaskSpec]
    estimated_total_steps: int
    reasoning: str


_PLANNING_PROMPT = """\
You are a master planner for an AI research system.

Analyze this query and create an execution plan.

QUERY: {query}

Available agent types:
- react:        Fast factual questions, 1-3 search steps
- reflexion:    Deep research requiring verification
- orchestrator: Multi-part questions
- rewoo:        Multi-step with known sequence upfront
- tree_search:  Ambiguous questions needing exploration

Assess:
1. COMPLEXITY: How complex is this? (1=trivial, 5=expert-level)
2. PLANNING LEVEL needed:
   - REACTIVE (2): Simple, answer likely in 1-2 steps
   - BATCH (3): Clear multi-step sequence
   - HIERARCHICAL (4): Requires breaking into sub-problems
3. TASKS: List the high-level tasks needed

Respond as JSON:
{{
  "complexity": 3,
  "planning_level": 3,
  "reasoning": "Why you chose this plan",
  "tasks": [
    {{
      "id": "T1",
      "description": "Search for X",
      "dependencies": [],
      "assigned_agent": "react",
      "estimated_complexity": 2
    }}
  ],
  "estimated_total_steps": 5
}}
"""


class TaskPlanner:
    """
    Autonomous task planner that analyzes queries and produces
    structured execution plans with agent assignments.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
    ) -> None:
        self._llm = llm_client
        self._model = model

    async def plan(self, query: str) -> ExecutionPlan:
        """Analyze query and produce an execution plan."""
        logger.info("planner.analyzing", query=query[:60])

        response = await self._llm.complete(
            messages=[
                Message(
                    role=Role.SYSTEM,
                    content="You are an expert AI task planner. Always respond with valid JSON.",
                ),
                Message(
                    role=Role.USER,
                    content=_PLANNING_PROMPT.format(query=query),
                ),
            ],
            model=self._model,
            temperature=0.0,
            max_tokens=1024,
        )

        raw = (response.content or "").strip()
        return self._parse_plan(query, raw)

    def _parse_plan(self, query: str, raw: str) -> ExecutionPlan:
        try:
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            data = json.loads(raw)

            tasks = [
                TaskSpec(
                    id=t["id"],
                    description=t["description"],
                    dependencies=t.get("dependencies", []),
                    assigned_agent=t.get("assigned_agent", "react"),
                    estimated_complexity=t.get("estimated_complexity", 1),
                )
                for t in data.get("tasks", [])
            ]

            level_num = data.get("planning_level", 2)
            try:
                level = PlanningLevel(level_num)
            except ValueError:
                level = PlanningLevel.REACTIVE

            return ExecutionPlan(
                query=query,
                planning_level=level,
                tasks=tasks,
                estimated_total_steps=data.get("estimated_total_steps", 3),
                reasoning=data.get("reasoning", ""),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("planner.parse_failed", error=str(exc))
            # Fallback: simple reactive plan
            return ExecutionPlan(
                query=query,
                planning_level=PlanningLevel.REACTIVE,
                tasks=[
                    TaskSpec(
                        id="T1",
                        description=f"Answer: {query}",
                        assigned_agent="react",
                    )
                ],
                estimated_total_steps=3,
                reasoning="Fallback to reactive planning due to parse error.",
            )

    def select_agent_type(self, plan: ExecutionPlan) -> str:
        """Map planning level and task structure to agent type."""
        if plan.planning_level == PlanningLevel.NONE:
            return "direct"
        elif plan.planning_level == PlanningLevel.REACTIVE:
            return "react"
        elif plan.planning_level == PlanningLevel.BATCH:
            return "rewoo"
        elif plan.planning_level == PlanningLevel.HIERARCHICAL:
            return "orchestrator"
        else:
            return "reflexion"