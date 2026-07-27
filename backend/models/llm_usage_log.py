"""
models/llm_usage_log.py — Phase 6

WHY THIS MODEL EXISTS
-----------------------
Mirrors `models/agent_execution_log.py`'s "one row per invocation" shape,
specifically for LLM calls — token accounting is one of this phase's
explicit requirements, and a structured, queryable log (not a text log
line) is what makes "total tokens spent this month" or "average latency
per model" answerable with a SQL query rather than log-scraping, the same
rationale Phase 1 gave for `AgentExecutionLog` itself.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LLMUsageLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "llm_usage_logs"

    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LLMUsageLog provider={self.provider} model={self.model_name} success={self.success}>"
