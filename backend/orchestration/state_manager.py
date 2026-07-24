"""
orchestration/state_manager.py — THE EXECUTION STATE MANAGER

WHY THIS FILE EXISTS
---------------------
`Task.status` (orchestration/task.py) is just a field — nothing stops
code elsewhere from setting it to an illegal value (e.g., `COMPLETED`
directly back to `RUNNING`) if it's mutated carelessly. This module is the
single place transitions are validated and centrally tracked, and — per
this phase's Message Bus requirement — the way it learns about state
changes is by *subscribing* to the `MessageBus`, not by being called
directly by the `WorkflowEngine`. This mirrors `EventLogger`'s identical
subscription pattern (orchestration/event_logger.py) — both are
independent observers of the same event stream, unaware of each other.
"""

from __future__ import annotations

from core.exceptions import AppException
from core.logging import get_logger
from orchestration.message_bus import Message, MessageBus
from orchestration.task import TaskStatus

logger = get_logger("agent")

_LEGAL_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.QUEUED: {TaskStatus.WAITING, TaskStatus.RUNNING, TaskStatus.SKIPPED, TaskStatus.CANCELLED},
    TaskStatus.WAITING: {TaskStatus.RUNNING, TaskStatus.SKIPPED, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.RETRYING},
    TaskStatus.RETRYING: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),  # terminal
    TaskStatus.FAILED: set(),  # terminal
    TaskStatus.SKIPPED: set(),  # terminal
    TaskStatus.CANCELLED: set(),  # terminal
}


class IllegalStateTransitionError(AppException):
    status_code = 500
    error_code = "illegal_state_transition"


class ExecutionStateManager:
    """
    Tracks every task's current status for one plan execution, subscribed
    to a `MessageBus` instance rather than called directly. Constructed
    fresh per execution (like the `MessageBus` it subscribes to) — task
    state from one Supervisor invocation must never leak into another.
    """

    def __init__(self, bus: MessageBus) -> None:
        self._states: dict[str, TaskStatus] = {}
        self._history: list[tuple[str, TaskStatus, TaskStatus]] = []  # (task_id, from, to)
        bus.subscribe_all(self._handle_message)

    def _handle_message(self, message: Message) -> None:
        task_id = message.payload.get("task_id")
        new_status_value = message.payload.get("status")
        if task_id is None or new_status_value is None:
            return  # not a task-state message — every other message type is ignored here
        self.set_status(task_id, TaskStatus(new_status_value))

    def set_status(self, task_id: str, new_status: TaskStatus) -> None:
        current = self._states.get(task_id)
        if current is not None:
            legal_next = _LEGAL_TRANSITIONS.get(current, set())
            if new_status not in legal_next and new_status != current:
                raise IllegalStateTransitionError(
                    f"Task {task_id} cannot transition from {current.value} to {new_status.value}"
                )
        self._history.append((task_id, current or new_status, new_status))
        self._states[task_id] = new_status

    def get_status(self, task_id: str) -> TaskStatus | None:
        return self._states.get(task_id)

    def snapshot(self) -> dict[str, TaskStatus]:
        return dict(self._states)

    def history_for(self, task_id: str) -> list[tuple[TaskStatus, TaskStatus]]:
        return [(frm, to) for tid, frm, to in self._history if tid == task_id]

    def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for status in self._states.values():
            counts[status.value] = counts.get(status.value, 0) + 1
        return counts
