"""
models/orchestration_event.py — Phase 5

WHY THIS MODEL EXISTS
-----------------------
`AgentExecutionLog` (Phase 1) already captures per-agent execution
telemetry (one row per agent invocation). This table captures a broader
category: orchestration-LEVEL events that don't belong to any single
agent — a plan being created, a task being skipped due to a failed
dependency, a retry being triggered, a plan completing. `EventLogger`
(orchestration/event_logger.py) is the only code that writes here,
subscribed to the `MessageBus` exactly like `ExecutionStateManager` is —
see that module's docstring.

HOW THIS PREPARES FOR THE FRONTEND
---------------------------------------
Per the Phase 5 brief's explicit mention: "Useful for future
visualization, frontend timelines, debugging." Storing `plan_id`,
`event_type`, and a JSON `payload` (not a rigid per-event-type schema)
means a future timeline UI can query "every event for plan X, in order"
with one indexed query, without this table needing a migration every time
a new event type is introduced.
"""

from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrchestrationEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "orchestration_events"

    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)

    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrchestrationEvent plan_id={self.plan_id} event_type={self.event_type}>"
