"""
orchestration/task.py — THE TASK MODEL

WHY THIS FILE EXISTS
---------------------
Every other orchestration component (`ExecutionPlan`, `WorkflowEngine`,
`AgentScheduler`, `ExecutionStateManager`) operates on `Task` objects —
this is the shared vocabulary the whole orchestration layer speaks. It is
deliberately a plain-dataclass model, not a database model: a task graph
lives only for the duration of one Supervisor invocation (mirroring
`core/agent_bus.py::TaskContext`'s "ephemeral, per-request" design from
Phase 1) — what gets persisted afterward is a *record* of what happened
(`orchestration/event_logger.py` + `models/orchestration_event.py`), not
the live task objects themselves.

RELATIONSHIP TO core/agent_bus.py::TaskContext
---------------------------------------------------
`TaskContext` (Phase 1) is the shared scratch space threaded through one
agent invocation chain — it answers "what data does this pipeline run
have." `Task` (this file) is a different, complementary concept: it
answers "what work needs to happen, in what order, by which agent, and
did it succeed." A single `Task`'s execution, when it runs, constructs and
uses a `TaskContext` internally (see `orchestration/workflow_engine.py`) —
the two were never meant to be the same object.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    WAITING = "waiting"  # blocked on an unfinished dependency
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # a dependency failed, so this task never ran
    CANCELLED = "cancelled"


class TaskPriority(int, enum.Enum):
    """
    Integer-valued so priorities are directly comparable/sortable — the
    `AgentScheduler` (orchestration/agent_scheduler.py) orders same-wave
    tasks by priority value ascending (LOW runs after HIGH within the same
    dependency wave, not across waves — dependencies always take
    precedence over priority).
    """

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class TaskError:
    """Structured failure information — never just a bare string."""

    message: str
    error_code: str | None = None
    is_retryable: bool = True
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TaskResult:
    """
    The outcome of one task's execution. Wraps the underlying
    `schemas.agent_response.AgentResult` (Phase 1's Confidence Framework)
    rather than duplicating its fields — a task's result IS an agent's
    result, plus orchestration-specific bookkeeping (which task produced
    it, how long the task itself took including retries).
    """

    task_id: str
    success: bool
    output: Any = None
    confidence: float | None = None
    execution_time_ms: int | None = None
    attempt_count: int = 1
    error: TaskError | None = None


@dataclass
class Task:
    """
    One unit of work in an `ExecutionPlan`. Identifies WHAT should happen
    (`capability`), by WHOM (`agent_name`, resolved by the AgentRegistry —
    see PlanBuilder), and its relationship to other tasks (`depends_on`).
    """

    capability: str
    agent_name: str | None = None  # resolved by PlanBuilder from `capability` via AgentRegistry
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: TaskPriority = TaskPriority.NORMAL
    depends_on: list[str] = field(default_factory=list)  # task IDs
    parent_task_id: str | None = None
    child_task_ids: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.QUEUED
    payload: dict[str, Any] = field(default_factory=dict)  # input data for the agent
    max_retries: int = 2
    timeout_seconds: float = 30.0
    result: TaskResult | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING
        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)

    def mark_completed(self, result: TaskResult) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, result: TaskResult) -> None:
        self.status = TaskStatus.FAILED
        self.result = result
        self.completed_at = datetime.now(timezone.utc)

    def mark_skipped(self, reason: str) -> None:
        self.status = TaskStatus.SKIPPED
        self.result = TaskResult(
            task_id=self.id, success=False, error=TaskError(message=reason, is_retryable=False)
        )
        self.completed_at = datetime.now(timezone.utc)

    @property
    def duration_ms(self) -> int | None:
        if self.started_at is None or self.completed_at is None:
            return None
        return int((self.completed_at - self.started_at).total_seconds() * 1000)
