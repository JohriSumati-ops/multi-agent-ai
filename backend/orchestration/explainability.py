"""
orchestration/explainability.py — DECISION TRACES

WHY THIS FILE EXISTS
---------------------
Per this phase's explicit requirement, every execution must explain: why
each agent was selected, why others weren't, the execution timeline, a
decision trace, confidence, and which memory/retrieval sources were used.
This module assembles that from data every other orchestration component
already produces (`ExecutionPlan`, `ExecutionContext`,
`ExecutionStateManager`) — it introduces no new bookkeeping of its own,
consistent with Phase 1's `schemas/explainability.py::Explanation` shape,
which this module builds on top of rather than duplicating.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from orchestration.agent_registry import AgentRegistry
from orchestration.context_builder import ExecutionContext
from orchestration.execution_plan import ExecutionPlan
from orchestration.task import Task, TaskStatus
from schemas.explainability import DecisionStep, EvidenceItem, Explanation


@dataclass
class TaskTimelineEntry:
    task_id: str
    capability: str
    agent_name: str | None
    status: str
    started_at: str | None
    completed_at: str | None
    duration_ms: int | None
    confidence: float | None


@dataclass
class DecisionTrace:
    plan_id: str
    goal: str
    timeline: list[TaskTimelineEntry] = field(default_factory=list)
    agent_selection_reasons: dict[str, str] = field(default_factory=dict)  # capability -> reason
    agents_not_selected: dict[str, str] = field(default_factory=dict)  # capability -> reason
    context_sources: dict[str, int] = field(default_factory=dict)
    explanation: Explanation | None = None


class ExplainabilityBuilder:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def build_trace(
        self, plan: ExecutionPlan, *, context: ExecutionContext | None = None
    ) -> DecisionTrace:
        timeline = [
            TaskTimelineEntry(
                task_id=task.id,
                capability=task.capability,
                agent_name=task.agent_name,
                status=task.status.value,
                started_at=task.started_at.isoformat() if task.started_at else None,
                completed_at=task.completed_at.isoformat() if task.completed_at else None,
                duration_ms=task.duration_ms,
                confidence=task.result.confidence if task.result else None,
            )
            for task in plan.tasks
        ]

        selected = {task.capability: self._selection_reason(task) for task in plan.tasks}
        not_selected = self._not_selected_reasons(plan)

        evidence = [
            EvidenceItem(description=f"Task '{t.capability}' completed successfully", source=t.agent_name, weight=1.0)
            for t in plan.successful_tasks()
        ] + [
            EvidenceItem(description=f"Task '{t.capability}' did not complete: {t.result.error.message if t.result and t.result.error else 'unknown'}", source=t.agent_name, weight=0.0)
            for t in plan.failed_tasks()
        ]

        decision_path = [
            DecisionStep(step_description=f"Selected {t.agent_name} for capability '{t.capability}'", agent_name="supervisor_agent")
            for t in plan.tasks
        ]

        overall_confidence = self._overall_confidence(plan)

        explanation = Explanation(
            reason=f"Plan '{plan.goal}' executed {len(plan.tasks)} task(s): "
            f"{len(plan.successful_tasks())} succeeded, {len(plan.failed_tasks())} failed/skipped.",
            evidence=evidence,
            confidence=overall_confidence,
            decision_path=decision_path,
        )

        return DecisionTrace(
            plan_id=plan.id,
            goal=plan.goal,
            timeline=timeline,
            agent_selection_reasons=selected,
            agents_not_selected=not_selected,
            context_sources=context.source_summary() if context else {},
            explanation=explanation,
        )

    def _selection_reason(self, task: Task) -> str:
        return f"'{task.agent_name}' is the registered agent for capability '{task.capability}'"

    def _not_selected_reasons(self, plan: ExecutionPlan) -> dict[str, str]:
        """
        Every registered capability NOT part of this plan, with a reason —
        satisfies "why another agent wasn't selected" explicitly.
        """
        requested = {t.capability for t in plan.tasks}
        reasons = {}
        for registration in self.registry.list():
            if registration.capability not in requested:
                reasons[registration.capability] = (
                    f"'{registration.agent_class.__name__}' provides capability "
                    f"'{registration.capability}', which this goal did not request."
                )
        return reasons

    @staticmethod
    def _overall_confidence(plan: ExecutionPlan) -> float | None:
        confidences = [t.result.confidence for t in plan.tasks if t.result and t.result.confidence is not None]
        if not confidences:
            return None
        return sum(confidences) / len(confidences)
