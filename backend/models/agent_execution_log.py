"""
models/agent_execution_log.py

WHY THIS MODEL EXISTS
-----------------------
Phase 1 requirement: infrastructure for agent execution logging must exist
before any agent does, so that the very first agent built in Phase 3 has
somewhere to write its execution record on day one — no schema change
needed when agents arrive.

This table is also the persistence backbone for the "Agent Activity
Timeline" frontend feature (Supervisor → Retriever → Memory → Reader →
Recommendation), since a timeline is just an ordered query of these rows
filtered by `task_id`.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Observability-as-a-first-class-citizen: this is structured, queryable
telemetry (as opposed to unstructured log lines), which is what makes it
possible to later answer questions like "which agent has the highest
average latency" or "what's our agent failure rate this week" with a SQL
query instead of grepping log files.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Every `BaseAgent.run()` call (see agents/base_agent.py) will, once agents
exist, wrap its execution and write exactly one row here per invocation via
`AgentExecutionLogRepository`. `task_id` groups every agent invocation that
happened while answering a single user request, which is what
`core/agent_bus.py`'s `TaskContext.task_id` is designed to populate.
"""

from __future__ import annotations

import enum

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentExecutionStatus(str, enum.Enum):
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AgentExecutionLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_execution_logs"

    # Groups every agent invocation belonging to a single user request.
    # Matches core.agent_bus.TaskContext.task_id — a plain string (not a
    # foreign key) because a task_id is transient and does not correspond
    # to a row in any other table.
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    user_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )

    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[AgentExecutionStatus] = mapped_column(
        default=AgentExecutionStatus.STARTED, nullable=False, index=True
    )

    # Sequencing within a task_id's timeline (Supervisor=0, Retriever=1, ...).
    step_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # --- Confidence Framework fields (see schemas/agent_response.py) ---
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Performance metrics ---
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_size_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_size_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured, agent-specific extras (e.g., which documents were
    # retrieved, which model was called) without needing a new column per
    # agent type. JSON (not Postgres-only JSONB) so the same model works
    # against SQLite in tests.
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AgentExecutionLog task_id={self.task_id} agent={self.agent_name} "
            f"status={self.status}>"
        )
