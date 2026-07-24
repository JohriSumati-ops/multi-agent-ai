"""
tests/test_agent_scheduler.py and ExecutionStateManager tests
"""

from __future__ import annotations

from orchestration.agent_scheduler import AgentScheduler
from orchestration.message_bus import MessageBus
from orchestration.state_manager import ExecutionStateManager, IllegalStateTransitionError
from orchestration.task import Task, TaskPriority, TaskStatus


def test_independent_tasks_are_all_runnable() -> None:
    t1, t2, t3 = Task(capability="a"), Task(capability="b"), Task(capability="c")
    scheduler = AgentScheduler()
    runnable = scheduler.get_runnable_tasks([t1, t2, t3])
    assert len(runnable) == 3


def test_dependent_task_not_runnable_until_dependency_completes() -> None:
    t1 = Task(capability="a")
    t2 = Task(capability="b", depends_on=[t1.id])
    scheduler = AgentScheduler()

    runnable = scheduler.get_runnable_tasks([t1, t2])
    assert [t.capability for t in runnable] == ["a"]
    assert t2.status == TaskStatus.WAITING

    t1.status = TaskStatus.COMPLETED
    runnable2 = scheduler.get_runnable_tasks([t1, t2])
    assert [t.capability for t in runnable2] == ["b"]


def test_runnable_tasks_sorted_by_priority_descending() -> None:
    low = Task(capability="low", priority=TaskPriority.LOW)
    high = Task(capability="high", priority=TaskPriority.HIGH)
    normal = Task(capability="normal", priority=TaskPriority.NORMAL)

    scheduler = AgentScheduler()
    runnable = scheduler.get_runnable_tasks([low, high, normal])
    assert [t.capability for t in runnable] == ["high", "normal", "low"]


def test_blocked_tasks_identified_when_dependency_failed() -> None:
    t1 = Task(capability="a")
    t2 = Task(capability="b", depends_on=[t1.id])
    t1.status = TaskStatus.FAILED

    scheduler = AgentScheduler()
    blocked = scheduler.get_blocked_tasks([t1, t2])
    assert [t.capability for t in blocked] == ["b"]


def test_blocked_tasks_identified_when_dependency_skipped() -> None:
    t1 = Task(capability="a")
    t2 = Task(capability="b", depends_on=[t1.id])
    t1.status = TaskStatus.SKIPPED

    scheduler = AgentScheduler()
    blocked = scheduler.get_blocked_tasks([t1, t2])
    assert len(blocked) == 1


def test_completed_tasks_are_never_runnable_again() -> None:
    t1 = Task(capability="a")
    t1.status = TaskStatus.COMPLETED
    scheduler = AgentScheduler()
    assert scheduler.get_runnable_tasks([t1]) == []


# ------------------------------------------------------------------ #
# ExecutionStateManager
# ------------------------------------------------------------------ #
def test_state_manager_tracks_status_via_message_bus() -> None:
    bus = MessageBus()
    manager = ExecutionStateManager(bus)
    bus.publish_event("task.state", payload={"task_id": "t1", "status": "running"})
    assert manager.get_status("t1") == TaskStatus.RUNNING


def test_state_manager_ignores_non_task_state_messages() -> None:
    bus = MessageBus()
    manager = ExecutionStateManager(bus)
    bus.publish_event("plan.started", payload={"plan_id": "p1"})
    assert manager.snapshot() == {}


def test_state_manager_rejects_illegal_transition() -> None:
    bus = MessageBus()
    manager = ExecutionStateManager(bus)
    manager.set_status("t1", TaskStatus.COMPLETED)
    try:
        manager.set_status("t1", TaskStatus.RUNNING)
        assert False, "expected IllegalStateTransitionError"
    except IllegalStateTransitionError:
        pass


def test_state_manager_allows_setting_the_same_status_again() -> None:
    bus = MessageBus()
    manager = ExecutionStateManager(bus)
    manager.set_status("t1", TaskStatus.RUNNING)
    manager.set_status("t1", TaskStatus.RUNNING)  # idempotent — should not raise
    assert manager.get_status("t1") == TaskStatus.RUNNING


def test_count_by_status_aggregates_correctly() -> None:
    bus = MessageBus()
    manager = ExecutionStateManager(bus)
    manager.set_status("t1", TaskStatus.COMPLETED)
    manager.set_status("t2", TaskStatus.COMPLETED)
    manager.set_status("t3", TaskStatus.FAILED)
    assert manager.count_by_status() == {"completed": 2, "failed": 1}


def test_history_for_task_records_transitions() -> None:
    bus = MessageBus()
    manager = ExecutionStateManager(bus)
    manager.set_status("t1", TaskStatus.RUNNING)
    manager.set_status("t1", TaskStatus.COMPLETED)
    history = manager.history_for("t1")
    assert history[-1] == (TaskStatus.RUNNING, TaskStatus.COMPLETED)
