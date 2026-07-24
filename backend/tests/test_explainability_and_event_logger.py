"""
tests/test_explainability_and_event_logger.py
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from core.exceptions import ValidationAppError
from orchestration.agent_registry import AgentRegistry
from orchestration.event_logger import EventLogger
from orchestration.execution_plan import PlanBuilder
from orchestration.explainability import ExplainabilityBuilder
from orchestration.message_bus import MessageBus
from orchestration.workflow_engine import WorkflowEngine


class _OkAgent(BaseAgent):
    name = "ok_agent"

    def execute(self, context):
        return "fine"


class _BadAgent(BaseAgent):
    name = "bad_agent"

    def execute(self, context):
        raise ValidationAppError("nope")


def test_decision_trace_includes_timeline_for_every_task() -> None:
    registry = AgentRegistry()
    registry.register("ok", _OkAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["ok"])
    WorkflowEngine(registry, MessageBus()).execute(plan)

    trace = ExplainabilityBuilder(registry).build_trace(plan)
    assert len(trace.timeline) == 1
    assert trace.timeline[0].status == "completed"


def test_decision_trace_reports_selection_reason() -> None:
    registry = AgentRegistry()
    registry.register("ok", _OkAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["ok"])
    WorkflowEngine(registry, MessageBus()).execute(plan)

    trace = ExplainabilityBuilder(registry).build_trace(plan)
    assert "ok" in trace.agent_selection_reasons
    assert "_OkAgent" in trace.agent_selection_reasons["ok"]


def test_decision_trace_reports_not_selected_capabilities() -> None:
    registry = AgentRegistry()
    registry.register("ok", _OkAgent)
    registry.register("unused", _OkAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["ok"])
    WorkflowEngine(registry, MessageBus()).execute(plan)

    trace = ExplainabilityBuilder(registry).build_trace(plan)
    assert "unused" in trace.agents_not_selected


def test_decision_trace_explanation_reflects_failures() -> None:
    registry = AgentRegistry()
    registry.register("bad", _BadAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["bad"])
    plan.tasks[0].max_retries = 0
    WorkflowEngine(registry, MessageBus()).execute(plan)

    trace = ExplainabilityBuilder(registry).build_trace(plan)
    assert "1 failed" in trace.explanation.reason
    assert len(trace.explanation.evidence) == 1
    assert trace.explanation.evidence[0].weight == 0.0


def test_decision_trace_context_sources_reflect_execution_context() -> None:
    from orchestration.context_builder import ExecutionContext

    registry = AgentRegistry()
    registry.register("ok", _OkAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["ok"])
    WorkflowEngine(registry, MessageBus()).execute(plan)

    context = ExecutionContext(user_id="u1", request_text="hi", short_term_memories=["a", "b"])
    trace = ExplainabilityBuilder(registry).build_trace(plan, context=context)
    assert trace.context_sources["short_term_memories"] == 2


# ------------------------------------------------------------------ #
# EventLogger
# ------------------------------------------------------------------ #
def test_event_logger_persists_events_from_message_bus(db_session) -> None:
    bus = MessageBus()
    logger = EventLogger(db_session, bus, plan_id="plan-123")

    bus.publish_event("task.started", payload={"task_id": "t1"})
    bus.publish_event("task.completed", payload={"task_id": "t1"})

    timeline = logger.get_timeline()
    assert len(timeline) == 2
    assert timeline[0].topic == "task.started"
    assert timeline[0].plan_id == "plan-123"


def test_event_logger_only_captures_events_for_its_own_plan(db_session) -> None:
    bus_a, bus_b = MessageBus(), MessageBus()
    logger_a = EventLogger(db_session, bus_a, plan_id="plan-a")
    EventLogger(db_session, bus_b, plan_id="plan-b")

    bus_a.publish_event("event", payload={})
    bus_b.publish_event("event", payload={})

    assert len(logger_a.get_timeline()) == 1


def test_event_logger_records_full_engine_execution(db_session) -> None:
    registry = AgentRegistry()
    registry.register("ok", _OkAgent)
    plan = PlanBuilder(registry).build_plan("goal", ["ok"])

    bus = MessageBus()
    logger = EventLogger(db_session, bus, plan_id=plan.id)
    WorkflowEngine(registry, bus).execute(plan)

    topics = [e.topic for e in logger.get_timeline()]
    assert "plan.started" in topics
    assert "plan.completed" in topics
