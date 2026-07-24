"""
agents/supervisor_agent.py — THE SUPERVISOR AGENT

WHY THIS FILE EXISTS
---------------------
The single new concrete agent Phase 5 adds. Per this phase's explicit,
repeated constraint, it NEVER parses a document, NEVER extracts metadata,
NEVER generates embeddings, NEVER answers a question — it only: builds
context (`ContextBuilder`), builds a plan (`PlanBuilder`), hands the plan
to the `WorkflowEngine`, and returns the result plus a `DecisionTrace`
(`ExplainabilityBuilder`). Every one of those four steps is delegated to a
component that was designed, built, and unit-tested independently — this
class is composition, not new logic.

WHY THIS INHERITS BaseAgent TOO
-------------------------------------
Even though `SupervisorAgent` operates one level above the other agents
(it orchestrates them, rather than being orchestrated), it still follows
`BaseAgent`'s Template Method contract — this means the Supervisor's own
invocation gets the same free timing/logging/error-containment every other
agent gets, and it lets a *future*, even-higher-level orchestrator (should
one ever be needed) invoke the Supervisor exactly like it would invoke any
other agent, through the same `run()`/`AgentResult` interface. This is the
Phase 0 architecture doc's original vision for the Supervisor Agent,
realized for the first time in this project.

INPUT / OUTPUT CONTRACT
----------------------------
Input via `context.intermediate_results`:
  - "goal": str — a human-readable description of what's being done
  - "capabilities": list[str] — which registered capabilities this
    request needs (see docs/Phase5.md Section 4 for why this is
    capability-driven rather than free-text-parsed)
  - "payload": dict — shared input data for the plan's tasks (e.g., a
    file path)
  - "user_id": UUID | None — for context building (memory/retrieval scoping)
  - "request_text": str | None — the user's raw request, for semantic
    context building

Output: `SupervisorResult`, containing the executed `ExecutionPlan` and
its `DecisionTrace`.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.config import settings
from core.exceptions import ValidationAppError
from orchestration.agent_registry import AgentRegistry, get_agent_registry
from orchestration.context_builder import ContextBuilder, ExecutionContext
from orchestration.event_logger import EventLogger
from orchestration.execution_plan import ExecutionPlan, PlanBuilder
from orchestration.explainability import DecisionTrace, ExplainabilityBuilder
from orchestration.message_bus import MessageBus
from orchestration.state_manager import ExecutionStateManager
from orchestration.workflow_engine import WorkflowEngine


@dataclass
class SupervisorResult:
    plan: ExecutionPlan
    trace: DecisionTrace
    context: ExecutionContext | None = None


class SupervisorAgent(BaseAgent):
    """
    Orchestrates a goal into an executed, explainable plan. Constructed
    with an optional `AgentRegistry` (defaults to the process-wide
    singleton via `get_agent_registry()`) purely for testability — tests
    construct their own isolated registry so agent registrations from one
    test never leak into another (see tests/test_supervisor_agent.py).
    """

    name = "supervisor_agent"

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self.registry = registry or get_agent_registry()

    def validate_input(self, context: TaskContext) -> None:
        if "goal" not in context.intermediate_results:
            raise ValidationAppError("SupervisorAgent requires 'goal' in intermediate_results")
        if "capabilities" not in context.intermediate_results:
            raise ValidationAppError("SupervisorAgent requires 'capabilities' (list[str]) in intermediate_results")

    def execute(self, context: TaskContext) -> SupervisorResult:
        goal: str = context.intermediate_results["goal"]
        capabilities: list[str] = context.intermediate_results["capabilities"]
        payload: dict = context.intermediate_results.get("payload", {})
        user_id: UUID | None = context.intermediate_results.get("user_id")
        request_text: str | None = context.intermediate_results.get("request_text")
        context_builder: ContextBuilder | None = context.intermediate_results.get("context_builder")
        db = context.intermediate_results.get("db")

        # --- Context building (Section 6) — optional: only when the
        # caller supplied a ContextBuilder AND a user_id/request_text.
        # A pure ingestion-style goal (e.g., "process this document") has
        # no need for memory/retrieval context, so this step is skipped
        # gracefully rather than forced. ---
        execution_context: ExecutionContext | None = None
        if context_builder is not None and user_id is not None and request_text is not None:
            execution_context = context_builder.build(user_id=user_id, request_text=request_text)

        # --- Planning (Section 4) ---
        plan = PlanBuilder(self.registry).build_plan(goal, capabilities, payload=payload)

        # --- Execution (Section 10) ---
        bus = MessageBus()
        state_manager = ExecutionStateManager(bus)  # noqa: F841 — kept alive so it stays subscribed for the run
        event_logger = None
        if db is not None:
            event_logger = EventLogger(db, bus, plan_id=plan.id, user_id=user_id)  # noqa: F841

        engine = WorkflowEngine(self.registry, bus, max_workers=settings.ORCHESTRATION_MAX_WORKERS)
        executed_plan = engine.execute(plan)

        # --- Explainability (Section 12) ---
        trace = ExplainabilityBuilder(self.registry).build_trace(executed_plan, context=execution_context)

        context.intermediate_results["supervisor_result"] = SupervisorResult(
            plan=executed_plan, trace=trace, context=execution_context
        )
        return context.intermediate_results["supervisor_result"]

    def validate_output(self, output: SupervisorResult) -> None:
        if not output.plan.tasks:
            raise ValidationAppError("SupervisorAgent produced a plan with zero tasks")
