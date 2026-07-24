"""
tests/test_execution_plan.py
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from orchestration.agent_registry import AgentRegistry, CapabilityNotRegisteredError
from orchestration.execution_plan import CyclicDependencyError, PlanBuilder
from orchestration.task import TaskStatus


class _StepAgent(BaseAgent):
    name = "step_agent"

    def execute(self, context):
        return "step done"


def _registry_with(*capability_deps: tuple[str, list[str]]) -> AgentRegistry:
    registry = AgentRegistry()
    for capability, deps in capability_deps:
        registry.register(capability, _StepAgent, depends_on_capabilities=deps)
    return registry


def test_build_plan_with_no_dependencies() -> None:
    registry = _registry_with(("a", []), ("b", []))
    plan = PlanBuilder(registry).build_plan("goal", ["a", "b"])
    assert len(plan.tasks) == 2
    assert all(not t.depends_on for t in plan.tasks)


def test_build_plan_resolves_dependencies() -> None:
    registry = _registry_with(("a", []), ("b", ["a"]))
    plan = PlanBuilder(registry).build_plan("goal", ["a", "b"])
    task_a = next(t for t in plan.tasks if t.capability == "a")
    task_b = next(t for t in plan.tasks if t.capability == "b")
    assert task_b.depends_on == [task_a.id]


def test_build_plan_omits_dependency_edge_when_dependency_not_requested() -> None:
    """Requesting 'b' without 'a' is valid — no edge is added since 'a' isn't part of this plan."""
    registry = _registry_with(("a", []), ("b", ["a"]))
    plan = PlanBuilder(registry).build_plan("goal", ["b"])
    task_b = plan.tasks[0]
    assert task_b.depends_on == []


def test_build_plan_raises_for_unregistered_capability() -> None:
    registry = AgentRegistry()
    try:
        PlanBuilder(registry).build_plan("goal", ["nonexistent"])
        assert False, "expected CapabilityNotRegisteredError"
    except CapabilityNotRegisteredError:
        pass


def test_build_plan_detects_cycles() -> None:
    registry = _registry_with(("a", ["b"]), ("b", ["a"]))
    try:
        PlanBuilder(registry).build_plan("goal", ["a", "b"])
        assert False, "expected CyclicDependencyError"
    except CyclicDependencyError:
        pass


def test_root_tasks_returns_tasks_with_no_dependencies() -> None:
    registry = _registry_with(("a", []), ("b", ["a"]))
    plan = PlanBuilder(registry).build_plan("goal", ["a", "b"])
    roots = plan.root_tasks()
    assert len(roots) == 1
    assert roots[0].capability == "a"


def test_is_complete_false_when_tasks_still_queued() -> None:
    registry = _registry_with(("a", []))
    plan = PlanBuilder(registry).build_plan("goal", ["a"])
    assert plan.is_complete() is False


def test_is_complete_true_when_all_tasks_terminal() -> None:
    registry = _registry_with(("a", []))
    plan = PlanBuilder(registry).build_plan("goal", ["a"])
    plan.tasks[0].status = TaskStatus.COMPLETED
    assert plan.is_complete() is True


def test_successful_and_failed_tasks_partition_correctly() -> None:
    registry = _registry_with(("a", []), ("b", []))
    plan = PlanBuilder(registry).build_plan("goal", ["a", "b"])
    plan.tasks[0].status = TaskStatus.COMPLETED
    plan.tasks[1].status = TaskStatus.FAILED
    assert len(plan.successful_tasks()) == 1
    assert len(plan.failed_tasks()) == 1


def test_get_task_by_id() -> None:
    registry = _registry_with(("a", []))
    plan = PlanBuilder(registry).build_plan("goal", ["a"])
    task = plan.tasks[0]
    assert plan.get_task(task.id) is task
    assert plan.get_task("nonexistent") is None


def test_plan_payload_is_shared_across_tasks() -> None:
    registry = _registry_with(("a", []), ("b", []))
    plan = PlanBuilder(registry).build_plan("goal", ["a", "b"], payload={"file_path": "/tmp/x"})
    assert all(t.payload["file_path"] == "/tmp/x" for t in plan.tasks)
