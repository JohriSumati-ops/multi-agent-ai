"""
models/conversation.py

WHY THIS MODEL EXISTS
-----------------------
Chat messages need to be grouped into sessions so a user can resume, title,
search, or delete a conversation as a unit, rather than as a flat, ungrouped
stream of messages. This is the parent side of the conversations/messages
parent-child pair described in Architecture Section 5.2.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Normalization: conversation-level metadata (title, associated documents)
changes rarely and is queried at low volume (e.g., rendering a sidebar
list); message-level data changes/append constantly and is queried at high
volume. Splitting them into two tables avoids bloating high-frequency
message inserts with rarely-changing parent columns.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
`document_ids` scopes which documents the Retrieval Agent should search
against for this conversation. The Conversation Agent (Phase 2) will read
`messages` (ordered by `created_at`) to build its short-term context
window.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversations"

    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(500), default="New Conversation", nullable=False)

    # Which documents this conversation's questions should be grounded in.
    # Stored as a JSON list of document UUIDs (as text) rather than a join
    # table for Phase 1 simplicity; may be normalized into a proper
    # many-to-many table if per-document conversation analytics are needed
    # later — a schema change isolated to this file and its repository.
    # JSON (not Postgres-only ARRAY) is used deliberately so the same model
    # works against both PostgreSQL in production and SQLite in tests.
    document_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Conversation id={self.id} title={self.title!r}>"
