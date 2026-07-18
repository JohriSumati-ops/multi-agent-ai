"""
models/memory.py

WHY THIS MODEL EXISTS
-----------------------
Architecture Section 3.2 deliberately separates "memory" from "raw
conversation logs": memory is synthesized insight (e.g., "user consistently
struggles with recursive base cases"), not a transcript. This table is the
persistence target for that synthesized insight, across all four memory
categories called out in the Phase 1 requirements.

DESIGN DECISION: single table + `memory_type` discriminator, not four
separate tables. All four memory kinds share the same shape (owner, content,
importance, optional expiry, optional scope to a conversation or document)
and will always be queried together for "give me everything relevant to
this user right now" — a single indexed table with a `memory_type` filter
is simpler to query across categories than four tables + UNION queries,
while still letting each category be filtered independently when needed.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Table-per-hierarchy modeling via a discriminator enum column, chosen over
table-per-type, because the four memory kinds are behaviorally identical at
the persistence layer and only differ in retrieval policy — and retrieval
policy belongs in the memory/ package's interfaces (see memory/interfaces.py),
not in the schema.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
- SHORT_TERM rows: written/read by the future Conversation Agent within a
  single session; `expires_at` lets old short-term entries be pruned.
- LONG_TERM rows: written by the future Memory Agent after significant
  events (quiz completion, repeated struggles); read at the start of every
  session to personalize agent behavior.
- CONVERSATION rows: scoped via `conversation_id`, e.g. "user asked
  clarifying questions about recursion in this thread."
- DOCUMENT rows: scoped via `document_id`, e.g. "user has revisited this
  document's Trees section three times."
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MemoryType(str, enum.Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    CONVERSATION = "conversation"
    DOCUMENT = "document"


class Memory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "memory"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    memory_type: Mapped[MemoryType] = mapped_column(nullable=False, index=True)

    # Optional scoping — only relevant for CONVERSATION / DOCUMENT memory
    # types; NULL for SHORT_TERM / LONG_TERM entries.
    conversation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True
    )
    document_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # How much weight this memory should carry when injected into a future
    # agent's context — set by the (future) Memory Agent, not by Phase 1.
    importance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # Only meaningful for SHORT_TERM entries; NULL means "does not expire."
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship(back_populates="memory_entries")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Memory id={self.id} type={self.memory_type} user_id={self.user_id}>"
