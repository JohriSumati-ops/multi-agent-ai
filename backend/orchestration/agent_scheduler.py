"""
orchestration/agent_scheduler.py — THE AGENT SCHEDULER

WHY THIS FILE EXISTS
---------------------
Separates "what order should tasks run in" (this file) from "actually run
them" (`workflow_engine.py`) — the same planner/executor split
`orchestration/execution_plan.py`'s docstring describes at the goal level,
applied here at the individual-task level. `AgentScheduler` answers one
question: given the current state of every task in a plan, which tasks are
eligible to run *right now*? The `WorkflowEngine` asks this question
repeatedly as execution proceeds (a task's dependency completing may make
new tasks eligible), rather than computing the full order once upfront —
this is what correctly handles tasks that fail: their dependents become
permanently ineligible (never runnable), not just temporarily blocked.

PRIORITY WITHIN A WAVE
---------------------------
All eligible tasks at a given moment form one "wave" (see docs/Phase5.md
Section 7 on execution graphs). Within a wave, `TaskPriority` breaks ties
for callers that want a hint about which task matters more (e.g., a
`WorkflowEngine` running sequentially, not in parallel, would use this
order) — but priority NEVER overrides a dependency relationship; a
CRITICAL task with an unmet dependency is never eligible before that
dependency completes.
"""

from __future__ import annotations

from orchestration.task import Task, TaskStatus


class AgentScheduler:
    def get_runnable_tasks(self, tasks: list[Task]) -> list[Task]:
        """
        Returns every task that is currently eligible to run: still
        `QUEUED`/`WAITING`, with every dependency in a `COMPLETED` state.
        Sorted by priority descending (highest priority first) — see
        module docstring for why this ordering is advisory, not authoritative.
        """
        by_id = {t.id: t for t in tasks}
        runnable = []
        for task in tasks:
            if task.status not in (TaskStatus.QUEUED, TaskStatus.WAITING):
                continue
            if self._dependencies_satisfied(task, by_id):
                runnable.append(task)
            else:
                task.status = TaskStatus.WAITING

        return sorted(runnable, key=lambda t: t.priority.value, reverse=True)

    def get_blocked_tasks(self, tasks: list[Task]) -> list[Task]:
        """
        Tasks that can never run because a dependency failed/was skipped
        — used by WorkflowEngine to propagate failure (mark these SKIPPED)
        rather than leaving them stuck in WAITING forever.
        """
        by_id = {t.id: t for t in tasks}
        blocked = []
        for task in tasks:
            if task.status not in (TaskStatus.QUEUED, TaskStatus.WAITING):
                continue
            if self._has_failed_dependency(task, by_id):
                blocked.append(task)
        return blocked

    @staticmethod
    def _dependencies_satisfied(task: Task, by_id: dict[str, Task]) -> bool:
        return all(by_id[dep_id].status == TaskStatus.COMPLETED for dep_id in task.depends_on)

    @staticmethod
    def _has_failed_dependency(task: Task, by_id: dict[str, Task]) -> bool:
        return any(
            by_id[dep_id].status in (TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED)
            for dep_id in task.depends_on
        )
