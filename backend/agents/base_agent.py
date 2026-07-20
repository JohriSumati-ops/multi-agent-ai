"""
agents/base_agent.py — THE AGENT INTERFACE

WHY THIS FILE EXISTS
---------------------
Requirement added after Phase 0 review: even though no agent is implemented
in Phase 1, every one of the sixteen future agents (Reading, Summarization,
Quiz, Recommendation, ...) must share a common interface so the Supervisor
can invoke any of them polymorphically, without a switch statement per
agent type.

NO AGENT LOGIC IS IMPLEMENTED HERE — this is an abstract base class only.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Template Method pattern: `run()` defines the fixed skeleton every agent
follows (validate input → do work → validate output → return a structured
result), while `execute()` is the one method each concrete agent actually
implements. This guarantees that logging, timing, and confidence-scoring
happen consistently for every agent, since that plumbing lives in `run()`,
not duplicated inside each of the sixteen future subclasses.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Phase 3's `SupervisorAgent`, `ReadingAgent`, `SummarizationAgent`, etc. will
all subclass `BaseAgent` and implement `execute()`. The `run()` method
defined here already wires up timing and AgentExecutionLog-shaped output,
so those future subclasses only need to write their actual reasoning logic.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from core.agent_bus import TaskContext
from core.logging import get_logger
from schemas.agent_response import AgentResult

logger = get_logger("agent")


class BaseAgent(ABC):
    """
    Abstract base every future agent inherits from.

    Concrete subclasses must implement:
      - `name` (class attribute): the agent's identifier, used in logs and
        in `Message.agent_name`.
      - `validate_input`: raise if the TaskContext is missing something
        this agent requires (e.g., Quiz Agent requires at least one active
        document).
      - `execute`: the agent's actual reasoning logic.
      - `validate_output`: raise if the produced output doesn't meet this
        agent's contract (e.g., a quiz must have at least one question).
    """

    name: str = "base_agent"

    def validate_input(self, context: TaskContext) -> None:
        """
        Override to assert preconditions on `context` before `execute` runs.
        Default implementation accepts anything — most agents will want to
        at least check that `context.original_query` is non-empty.
        """
        return None

    @abstractmethod
    def execute(self, context: TaskContext) -> Any:
        """
        The agent's actual work. Must be implemented by every concrete
        subclass. Not implemented for any agent in Phase 1.
        """
        raise NotImplementedError

    def validate_output(self, output: Any) -> None:
        """
        Override to assert postconditions on the raw output of `execute`
        before it's wrapped into an AgentResult. Default accepts anything.
        """
        return None

    def run(self, context: TaskContext) -> AgentResult:
        """
        The fixed orchestration skeleton. Concrete agents should NOT
        override this — override `execute` instead.

        Responsibilities handled here so every agent gets them for free:
          1. Input validation
          2. Timing (feeds `AgentResult.execution_time_ms`)
          3. Output validation
          4. Structured error handling (never lets a raw exception escape
             to the Supervisor — always returns an AgentResult, even on
             failure, so the Supervisor's aggregation logic doesn't need
             a separate exception-handling path per agent)
          5. Recording a step in the shared TaskContext's execution trace
        """
        started_at = time.perf_counter()
        try:
            self.validate_input(context)
            output = self.execute(context)
            self.validate_output(output)

            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            context.record_step(self.name, "completed successfully", latency_ms=elapsed_ms)

            return AgentResult(
                agent_name=self.name,
                success=True,
                output=output,
                execution_time_ms=elapsed_ms,
            )
        except Exception as exc:  # noqa: BLE001 — intentionally broad: this
            # boundary must never let an agent's internal failure crash the
            # Supervisor's aggregation loop; the error is captured in the
            # result instead.
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            logger.exception("Agent %s failed during execution", self.name)
            context.record_step(self.name, "failed", latency_ms=elapsed_ms, error=str(exc))

            # If this was one of our own domain exceptions (see
            # core/exceptions.py), preserve its error_code/status_code so
            # a caller reconstructing a typed exception downstream (see
            # document_processing/pipeline.py) doesn't lose that
            # information — only the string survives otherwise.
            error_code = getattr(exc, "error_code", None)
            error_status_code = getattr(exc, "status_code", None)

            return AgentResult(
                agent_name=self.name,
                success=False,
                execution_time_ms=elapsed_ms,
                error_message=str(exc),
                error_code=error_code,
                error_status_code=error_status_code,
            )
