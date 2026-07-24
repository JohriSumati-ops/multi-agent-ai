"""
tests/test_workflow_engine.py

Exercises WorkflowEngine against both real registered agents (the three
that exist: PDF parsing, metadata extraction, embedding) and small
purpose-built fake agents (for controlled failure/retry/timeout testing) —
mirroring how earlier phases mixed real-agent and fake-agent tests.
"""

from __future__ import annotations

import time

from agents.base_agent import BaseAgent
from core.exceptions import ValidationAppError
from models.document import DocumentFormat
from orchestration.agent_registry import AgentRegistry
from orchestration.execution_plan import PlanBuilder
from orchestration.message_bus import MessageBus
from orchestration.task import TaskStatus
from orchestration.workflow_engine import WorkflowEngine


class _AlwaysSucceedsAgent(BaseAgent):
    name = "always_succeeds"

    def execute(self, context):
        return "ok"


class _AlwaysFailsAgent(BaseAgent):
    name = "always_fails"

    def execute(self, context):
        raise ValidationAppError("intentional failure")


class _FailsTwiceThenSucceedsAgent(BaseAgent):
    name = "flaky"
    _attempts: dict[int, int] = {}

    def execute(self, context):
        key = id(context)
        self._attempts[key] = self._attempts.get(key, 0) + 1
        if self._attempts[key] < 3:
            raise ValidationAppError("transient failure")
        return "succeeded on attempt 3"


class _SlowAgent(BaseAgent):
    name = "slow"

    def execute(self, context):
        time.sleep(2)
        return "too slow"


def test_engine_executes_a_single_task_successfully() -> None:
    registry = AgentRegistry()
    registry.register("succeed", _AlwaysSucceedsAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["succeed"])

    engine = WorkflowEngine(registry, MessageBus())
    result = engine.execute(plan)

    assert result.tasks[0].status == TaskStatus.COMPLETED
    assert result.tasks[0].result.output == "ok"


def test_engine_respects_dependency_order_with_real_agents(tmp_path) -> None:
    from orchestration.agent_registry import get_agent_registry

    registry = get_agent_registry()
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Graphs generalize trees by allowing cycles between nodes.")

    plan = PlanBuilder(registry).build_plan(
        "process document",
        ["parse_document", "extract_metadata"],
        payload={"file_path": str(file_path), "file_format": DocumentFormat.TXT, "original_filename": "sample.txt"},
    )
    engine = WorkflowEngine(registry, MessageBus())
    result = engine.execute(plan)

    assert all(t.status == TaskStatus.COMPLETED for t in result.tasks)
    metadata_task = next(t for t in result.tasks if t.capability == "extract_metadata")
    assert metadata_task.result.output.word_count > 0


def test_engine_marks_task_failed_after_exhausting_retries() -> None:
    registry = AgentRegistry()
    registry.register("fail", _AlwaysFailsAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["fail"])
    plan.tasks[0].max_retries = 2

    engine = WorkflowEngine(registry, MessageBus())
    result = engine.execute(plan)

    task = result.tasks[0]
    assert task.status == TaskStatus.FAILED
    assert task.result.attempt_count == 3  # initial attempt + 2 retries


def test_engine_retries_and_recovers_from_transient_failure() -> None:
    registry = AgentRegistry()
    registry.register("flaky", _FailsTwiceThenSucceedsAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["flaky"])
    plan.tasks[0].max_retries = 3

    engine = WorkflowEngine(registry, MessageBus())
    result = engine.execute(plan)

    task = result.tasks[0]
    assert task.status == TaskStatus.COMPLETED
    assert task.result.attempt_count == 3


def test_engine_propagates_failure_to_dependent_tasks() -> None:
    registry = AgentRegistry()
    registry.register("fail", _AlwaysFailsAgent)
    registry.register("dependent", _AlwaysSucceedsAgent, depends_on_capabilities=["fail"])
    plan = PlanBuilder(registry).build_plan("goal", ["fail", "dependent"])
    plan.tasks[0].max_retries = 0

    engine = WorkflowEngine(registry, MessageBus())
    result = engine.execute(plan)

    fail_task = next(t for t in result.tasks if t.capability == "fail")
    dependent_task = next(t for t in result.tasks if t.capability == "dependent")
    assert fail_task.status == TaskStatus.FAILED
    assert dependent_task.status == TaskStatus.SKIPPED


def test_engine_continues_independent_branches_after_one_fails() -> None:
    """Partial completion: an independent, unrelated task must still succeed."""
    registry = AgentRegistry()
    registry.register("fail", _AlwaysFailsAgent)
    registry.register("independent", _AlwaysSucceedsAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["fail", "independent"])
    plan.tasks[0].max_retries = 0

    engine = WorkflowEngine(registry, MessageBus())
    result = engine.execute(plan)

    independent_task = next(t for t in result.tasks if t.capability == "independent")
    assert independent_task.status == TaskStatus.COMPLETED


def test_engine_enforces_task_timeout_without_blocking() -> None:
    registry = AgentRegistry()
    registry.register("slow", _SlowAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["slow"])
    plan.tasks[0].timeout_seconds = 0.2
    plan.tasks[0].max_retries = 0

    engine = WorkflowEngine(registry, MessageBus())
    start = time.time()
    result = engine.execute(plan)
    elapsed = time.time() - start

    assert result.tasks[0].status == TaskStatus.FAILED
    assert "timed out" in result.tasks[0].result.error.message
    assert elapsed < 1.0  # must not have waited for the full 2-second sleep


def test_engine_publishes_lifecycle_messages() -> None:
    registry = AgentRegistry()
    registry.register("succeed", _AlwaysSucceedsAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["succeed"])

    bus = MessageBus()
    engine = WorkflowEngine(registry, bus)
    engine.execute(plan)

    topics = [m.topic for m in bus.history()]
    assert "plan.started" in topics
    assert "task.started" in topics
    assert "task.completed" in topics
    assert "plan.completed" in topics


def test_cancel_marks_remaining_tasks_cancelled() -> None:
    registry = AgentRegistry()
    registry.register("a", _AlwaysSucceedsAgent)
    registry.register("b", _AlwaysSucceedsAgent, depends_on_capabilities=["a"])
    plan = PlanBuilder(registry).build_plan("goal", ["a", "b"])

    bus = MessageBus()
    engine = WorkflowEngine(registry, bus)
    engine.cancel()  # cancel before execute() even starts
    result = engine.execute(plan)

    assert all(t.status == TaskStatus.CANCELLED for t in result.tasks)


def test_parallel_independent_tasks_all_complete() -> None:
    registry = AgentRegistry()
    for i in range(4):
        registry.register(f"task_{i}", _AlwaysSucceedsAgent)
    plan = PlanBuilder(registry).build_plan("goal", [f"task_{i}" for i in range(4)])

    engine = WorkflowEngine(registry, MessageBus(), max_workers=4)
    result = engine.execute(plan)

    assert all(t.status == TaskStatus.COMPLETED for t in result.tasks)
