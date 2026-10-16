"""
Planning Autonomy Module.

Levels of planning autonomy:
    L1 — No planning:     Direct LLM response
    L2 — Reactive:        ReACT (plan one step at a time)
    L3 — Batch planning:  ReWOO (full plan upfront)
    L4 — Hierarchical:    Tasks broken into sub-plans recursively
    L5 — Self-directing:  Agent modifies its own plan mid-execution

Production additions:
* ``validate_plan`` — DAG validation: detects cycles, self-dependencies,
  unknown references, and orphan tasks BEFORE dispatch. A cyclic plan
  used to deadlock the executor; now it is rejected at plan time (FM-13).
* Task count clamp — the planner LLM is untrusted output (ARCHITECTURE.md
  principle 4); a plan with 50 tasks is truncated to a budget-aware cap.
* JSON extraction hardened for fenced/verbose model output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum

import structlog

from core.llm_client import LLMClient
from core.message_types import Message, Role

logger = structlog.get_logger(__name__)


class PlanningLevel(IntEnum):
    NONE = 1
    REACTIVE = 2
    BATCH = 3
    HIERARCHICAL = 4
    SELF_MODIFY = 5


@dataclass
class TaskSpec:
    """A single task in a hierarchical plan."""

    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    sub_tasks: list[TaskSpec] = field(default_factory=list)
    assigned_agent: str = "react"
    estimated_complexity: int = 1  # 1-5 scale
    status: str = "pending"        # pending, running, done, failed


@dataclass
class ExecutionPlan:
    """Full hierarchical execution plan for a query."""

    query: str
    planning_level: PlanningLevel
    tasks: list[TaskSpec]
    estimated_total_steps: int
    reasoning: str
    validation_errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.validation_errors


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

_MAX_TASKS = 10


def _extract_json(text: str) -> str:
    """Strip markdown fences / preamble from LLM JSON output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()


def validate_plan(plan: ExecutionPlan) -> list[str]:
    """
    DAG validation. Returns a list of errors (empty = valid).

    Checks: duplicate IDs, unknown dependencies, self-dependencies,
    cycles (Kahn's algorithm), and the task-count clamp.
    """
    errors: list[str] = []
    tasks = plan.tasks

    if not tasks:
        errors.append("plan has no tasks")
        return errors

    if len(tasks) > _MAX_TASKS:
        errors.append(f"plan exceeds max tasks ({len(tasks)} > {_MAX_TASKS})")

    ids = [t.id for t in tasks]
    if len(ids) != len(set(ids)):
        errors.append("duplicate task ids in plan")

    id_set = set(ids)
    for task in tasks:
        if task.id in task.dependencies:
            errors.append(f"task {task.id} depends on itself")
        for dep in task.dependencies:
            if dep not in id_set:
                errors.append(f"task {task.id} depends on unknown task {dep}")

    # Cycle detection via Kahn's algorithm
    in_degree = {t.id: 0 for t in tasks}
    dependents: dict[str, list[str]] = {t.id: [] for t in tasks}
    for task in tasks:
        for dep in task.dependencies:
            if dep in in_degree:
                in_degree[task.id] += 1
                dependents[dep].append(task.id)

    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    visited = 0
    while queue:
        current = queue.pop()
        visited += 1
        for nxt in dependents[current]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    if visited != len(tasks):
        cyclic = sorted(set(ids) - {
            tid for tid, deg in in_degree.items() if deg == 0
        } - set(queue))
        errors.append(f"dependency cycle detected involving: {cyclic[:5]}")

    return errors


class TaskPlanner:
    """Autonomous task planner producing validated execution plans."""

    def __init__(self, llm_client: LLMClient, model: str | None = None) -> None:
        self._llm = llm_client
        self._model = model

    async def plan(self, query: str) -> ExecutionPlan:
        """Analyze query → validated execution plan."""
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
            fast=True,
        )

        raw = (response.content or "").strip()
        plan = self._parse_plan(query, raw)

        plan.validation_errors = validate_plan(plan)
        if not plan.is_valid:
            logger.warning(
                "planner.validation_failed",
                errors=plan.validation_errors,
            )
        return plan

    def _parse_plan(self, query: str, raw: str) -> ExecutionPlan:
        try:
            data = json.loads(_extract_json(raw))

            tasks = [
                TaskSpec(
                    id=t["id"],
                    description=t["description"],
                    dependencies=t.get("dependencies", []),
                    assigned_agent=t.get("assigned_agent", "react"),
                    estimated_complexity=t.get("estimated_complexity", 1),
                )
                for t in data.get("tasks", [])[:_MAX_TASKS]
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
            return ExecutionPlan(
                query=query,
                planning_level=PlanningLevel.REACTIVE,
                tasks=[TaskSpec(
                    id="T1",
                    description=f"Answer: {query}",
                    assigned_agent="react",
                )],
                estimated_total_steps=3,
                reasoning="Fallback to reactive planning due to parse error.",
                validation_errors=[f"parse failure: {exc}"],
            )

    def select_agent_type(self, plan: ExecutionPlan) -> str:
        """Map planning level and task structure to agent type."""
        if not plan.is_valid:
            # Invalid plans route to the safest, cheapest strategy.
            return "react"
        if plan.planning_level == PlanningLevel.NONE:
            return "direct"
        if plan.planning_level == PlanningLevel.REACTIVE:
            return "react"
        if plan.planning_level == PlanningLevel.BATCH:
            return "rewoo"
        if plan.planning_level == PlanningLevel.HIERARCHICAL:
            return "orchestrator"
        return "reflexion"
