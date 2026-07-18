"""
core/agent_bus.py

WHY THIS FILE EXISTS
---------------------
The approved architecture (Section 6.1) specifies that agents never call
each other directly — all coordination flows through the Supervisor via a
shared task-context object. Phase 1 has no Supervisor and no agents yet, but
the *shape* of that shared context is a contract the whole system will
depend on, so it is defined here first, independent of any specific agent.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Defining a shared data contract (`TaskContext`) before the components that
use it exist is a form of "design by contract" — it lets Phase 3's
Supervisor and every individual agent be built against a stable interface,
developed and tested independently, and integrated later with no surprises.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
- Phase 3: `SupervisorAgent` will construct a `TaskContext` per incoming
  request and pass a (possibly scoped) copy to each agent it invokes.
- Every agent's `run()` method (see agents/base_agent.py) will accept a
  `TaskContext` and return an `AgentResult` (schemas/agent_response.py).
- The AgentExecutionLog repository will persist one row per `TaskContext`
  step, which is what powers the "Agent Activity Timeline" UI feature.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskContext:
    """
    The shared object threaded through a single user request as it moves
    through the Supervisor and any agents it invokes.

    Deliberately a plain dataclass, not an ORM model — this object lives
    only for the duration of one request/response cycle and is never
    persisted wholesale. What DOES get persisted (see models/agent_execution_log.py)
    is a structured summary of what happened at each step.
    """

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str | None = None
    conversation_id: str | None = None
    original_query: str = ""
    active_document_ids: list[str] = field(default_factory=list)

    # Populated incrementally as agents run. Each entry is a lightweight
    # record of one agent's contribution — NOT the full AgentResult object,
    # to keep the context object cheap to pass around.
    execution_trace: list[dict[str, Any]] = field(default_factory=list)

    # Free-form scratch space for intermediate agent outputs that a later
    # agent in the same request needs (e.g., Retrieval Agent's chunks
    # consumed by the Reading Agent). Keyed by producing agent name.
    intermediate_results: dict[str, Any] = field(default_factory=dict)

    def record_step(self, agent_name: str, summary: str, **extra: Any) -> None:
        """Append a lightweight trace entry. Called by agents after they run."""
        self.execution_trace.append({"agent": agent_name, "summary": summary, **extra})


class AgentBus:
    """
    Placeholder coordination point for future agent-to-Supervisor messaging.

    Phase 1 note: this class intentionally does nothing yet beyond holding
    the interface shape. It exists so that `services/` code written today
    can already depend on "a bus exists" without knowing its eventual
    implementation (in-process function calls vs. a real message queue).
    """

    def __init__(self) -> None:
        self._context: TaskContext | None = None

    def start_task(self, **kwargs: Any) -> TaskContext:
        self._context = TaskContext(**kwargs)
        return self._context

    def current_context(self) -> TaskContext | None:
        return self._context
