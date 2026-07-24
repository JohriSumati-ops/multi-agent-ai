"""
tests/test_task_model.py
"""

from __future__ import annotations

from orchestration.task import Task, TaskError, TaskPriority, TaskResult, TaskStatus


def test_task_starts_queued() -> None:
    task = Task(capability="parse_document")
    assert task.status == TaskStatus.QUEUED
    assert task.result is None


def test_task_has_unique_id() -> None:
    t1 = Task(capability="a")
    t2 = Task(capability="a")
    assert t1.id != t2.id


def test_mark_running_sets_started_at() -> None:
    task = Task(capability="a")
    assert task.started_at is None
    task.mark_running()
    assert task.status == TaskStatus.RUNNING
    assert task.started_at is not None


def test_mark_running_does_not_overwrite_started_at_on_retry() -> None:
    task = Task(capability="a")
    task.mark_running()
    first_start = task.started_at
    task.mark_running()  # simulates a retry re-entering RUNNING
    assert task.started_at == first_start


def test_mark_completed_sets_result_and_timestamp() -> None:
    task = Task(capability="a")
    task.mark_running()
    result = TaskResult(task_id=task.id, success=True, output="done")
    task.mark_completed(result)
    assert task.status == TaskStatus.COMPLETED
    assert task.result is result
    assert task.completed_at is not None


def test_mark_failed_sets_result() -> None:
    task = Task(capability="a")
    task.mark_running()
    result = TaskResult(task_id=task.id, success=False, error=TaskError(message="boom"))
    task.mark_failed(result)
    assert task.status == TaskStatus.FAILED
    assert task.result.error.message == "boom"


def test_mark_skipped_creates_a_failure_result_with_reason() -> None:
    task = Task(capability="a")
    task.mark_skipped("dependency failed")
    assert task.status == TaskStatus.SKIPPED
    assert task.result.success is False
    assert task.result.error.message == "dependency failed"
    assert task.result.error.is_retryable is False


def test_duration_ms_is_none_until_both_timestamps_set() -> None:
    task = Task(capability="a")
    assert task.duration_ms is None
    task.mark_running()
    assert task.duration_ms is None
    task.mark_completed(TaskResult(task_id=task.id, success=True))
    assert task.duration_ms is not None
    assert task.duration_ms >= 0


def test_task_priority_ordering() -> None:
    assert TaskPriority.CRITICAL > TaskPriority.HIGH > TaskPriority.NORMAL > TaskPriority.LOW


def test_task_default_priority_is_normal() -> None:
    task = Task(capability="a")
    assert task.priority == TaskPriority.NORMAL


def test_task_default_retries_and_timeout() -> None:
    task = Task(capability="a")
    assert task.max_retries == 2
    assert task.timeout_seconds == 30.0


def test_task_supports_parent_child_relationship() -> None:
    parent = Task(capability="parent_capability")
    child = Task(capability="child_capability", parent_task_id=parent.id)
    parent.child_task_ids.append(child.id)
    assert child.parent_task_id == parent.id
    assert child.id in parent.child_task_ids
