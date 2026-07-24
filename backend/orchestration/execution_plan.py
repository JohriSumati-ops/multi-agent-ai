"""
orchestration/execution_plan.py — THE EXECUTION GRAPH + PLANNER

WHY THIS FILE EXISTS
---------------------
Converts a user goal into an ordered task graph — see docs/Phase5.md
Section 4 for the full "planning without an LLM" rationale. `PlanBuilder`
is deliberately simple and rule-based: given a list of requested
capabilities, it looks each one up in the `AgentRegistry`, and uses each
capability's *declared* `depends_on_capabilities` (set at registration
time — see agent_registry.py's `_register_default_agents`) to wire up
`Task.depends_on` correctly. No goal-understanding, no free-text parsing,
no model inference happens here — that is precisely the point.

WHY A SEPARATE `ExecutionPlan` OBJECT (NOT JUST `list[Task]`)
--------------------------------------------------------------------
A plan needs its own identity (a `plan_id`) for the `EventLogger` and
`DecisionTrace` to reference, and needs helper methods (`get_task`,
`root_tasks`, `is_complete`) that don't belong on the `Task` dataclass
itself — keeping `Task` a pure data record and `ExecutionPlan` the object
with graph-level behavior is the same separation Phase 1 applied between
`models/` (data) and `repositories/`/`services/` (behavior on that data).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from core.exceptions import AppException
from orchestration.agent_registry import AgentRegistry
from orchestration.task import Task, TaskPriority, TaskStatus


class CyclicDependencyError(AppException):
    status_code = 422
    error_code = "cyclic_dependency"


class UnknownDependencyError(AppException):
    status_code = 422
    error_code = "unknown_dependency"


@dataclass
class ExecutionPlan:
    goal: str
    tasks: list[Task] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get_task(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def root_tasks(self) -> list[Task]:
        """Tasks with no dependencies — always eligible to run first."""
        return [t for t in self.tasks if not t.depends_on]

    def is_complete(self) -> bool:
        """True once every task has reached a terminal state."""
        terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED}
        return all(t.status in terminal for t in self.tasks)

    def successful_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.COMPLETED]

    def failed_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.status in (TaskStatus.FAILED, TaskStatus.SKIPPED)]


def _detect_cycle(tasks: list[Task]) -> None:
    """
    Simple DFS cycle detection over `depends_on` edges. Raises
    `CyclicDependencyError` if one exists — a cyclic plan can never
    complete (every task in the cycle would wait forever), so this is
    checked eagerly at plan-build time rather than discovered later as a
    stuck WorkflowEngine.
    """
    by_id = {t.id: t for t in tasks}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t.id: WHITE for t in tasks}

    def visit(task_id: str) -> None:
        color[task_id] = GRAY
        for dep_id in by_id[task_id].depends_on:
            if dep_id not in by_id:
                raise UnknownDependencyError(f"Task '{task_id}' depends on unknown task '{dep_id}'")
            if color[dep_id] == GRAY:
                raise CyclicDependencyError(f"Cyclic dependency detected involving task '{task_id}'")
            if color[dep_id] == WHITE:
                visit(dep_id)
        color[task_id] = BLACK

    for task in tasks:
        if color[task.id] == WHITE:
            visit(task.id)


class PlanBuilder:
    """
    Builds an `ExecutionPlan` from a goal + an ordered list of requested
    capabilities, resolving each capability's agent and dependencies via
    the `AgentRegistry`.
    """

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def build_plan(
        self,
        goal: str,
        capabilities: list[str],
        *,
        payload: dict | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> ExecutionPlan:
        """
        `capabilities` is the caller's requested set (e.g.,
        `["parse_document", "extract_metadata", "generate_embeddings"]`);
        `payload` is shared input data available to every task (e.g., a
        file path) — individual agents pick out what they need from it,
        exactly like `TaskContext.intermediate_results` already does for
        the Phase 2 pipeline.

        Dependencies come from each capability's REGISTERED
        `depends_on_capabilities`, filtered down to only the dependencies
        the caller actually requested — requesting `extract_metadata`
        without `parse_document` is valid (the caller may already have
        parsed content in `payload`); the dependency edge is only added
        when both capabilities are part of the same plan.
        """
        capability_to_task: dict[str, Task] = {}
        tasks: list[Task] = []

        for capability in capabilities:
            registration = self.registry.get(capability)  # raises CapabilityNotRegisteredError if missing
            task = Task(
                capability=capability,
                agent_name=registration.agent_class.__name__,
                priority=priority,
                payload=dict(payload or {}),
            )
            capability_to_task[capability] = task
            tasks.append(task)

        for capability, task in capability_to_task.items():
            registration = self.registry.get(capability)
            for dep_capability in registration.depends_on_capabilities:
                dep_task = capability_to_task.get(dep_capability)
                if dep_task is not None:
                    task.depends_on.append(dep_task.id)

        _detect_cycle(tasks)  # fail fast rather than deadlock at execution time

        return ExecutionPlan(goal=goal, tasks=tasks)
