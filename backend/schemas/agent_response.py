"""
schemas/agent_response.py — THE CONFIDENCE FRAMEWORK

WHY THIS FILE EXISTS
---------------------
This is infrastructure requested explicitly by the Phase 1 review: every
future agent (Reading, Quiz, Recommendation, ...) must return a response in
a common shape so the Supervisor, the logging layer, and the frontend can
all treat "an agent's answer" as one predictable type, regardless of which
of the sixteen agents produced it.

No agent exists yet in Phase 1. This file defines the contract those
agents will return so that the Supervisor Agent (Phase 3) can be written
against a stable type from day one, instead of sixteen ad hoc return
shapes.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
This is the "Envelope" / "Result Object" pattern applied to AI outputs
specifically: instead of an agent returning a bare string, it returns a
structured object that carries the answer PLUS the metadata needed to
trust, log, explain, and debug that answer.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
`agents/base_agent.py`'s abstract `run()` method is typed to return
`AgentResult`. The Explainability Agent (Phase 5) consumes
`AgentResult.explanation` directly. The AgentExecutionLog repository
persists `confidence_score`, `execution_time_ms`, and `source` from this
object after every agent call.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from schemas.explainability import Explanation


class ConfidenceSource(str, Enum):
    """
    Where a confidence score came from — kept explicit because "0.82" means
    something very different depending on how it was produced, and any
    consumer (UI, logging, downstream agent) needs to know which.
    """

    MODEL_LOGPROB = "model_logprob"
    RETRIEVAL_SIMILARITY = "retrieval_similarity"
    HEURISTIC = "heuristic"
    SELF_REPORTED = "self_reported"  # the LLM asked to rate its own confidence
    NOT_APPLICABLE = "not_applicable"


class AgentResult(BaseModel):
    """
    The universal return type for every future agent's `run()` method.

    Fields map directly to the Phase 1 "Confidence Framework" requirement:
    confidence_score, execution_time, source, reason, metadata.
    """

    agent_name: str
    success: bool

    # The agent's actual output. Left as `Any` here deliberately — a Quiz
    # Agent returns a list of questions, a Reading Agent returns a string
    # explanation, a Comparison Agent returns a structured table. Each
    # concrete agent subclass is expected to also expose a narrower,
    # typed accessor in its own module; this base stays generic on purpose.
    output: Any = None

    confidence_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="0.0-1.0 confidence in `output`."
    )
    confidence_source: ConfidenceSource = ConfidenceSource.NOT_APPLICABLE

    execution_time_ms: int | None = None

    # Short, human-readable justification — the one-line version of
    # `explanation` below, suitable for a tooltip.
    reason: str | None = None

    # Full structured explanation, when the caller needs more than one
    # line (see schemas/explainability.py).
    explanation: Explanation | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    error_code: str | None = None
    error_status_code: int | None = None
