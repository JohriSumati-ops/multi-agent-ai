"""
models/message.py

WHY THIS MODEL EXISTS
-----------------------
The atomic unit of a chat: one turn, by one role (user or assistant), at one
point in time. Kept separate from `Conversation` per the normalization
rationale documented there.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Append-only log modeling: messages are never updated or reordered after
creation (only inserted), which is why there's no need for a separate
"draft" or "edited" state machine here — that simplicity is a direct result
of correctly identifying this table's access pattern.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
`agent_name` records which agent(s) produced an assistant message — this is
what lets the frontend's AgentActivityIndicator (Section 4.4) show
"Reading Agent" or "Quiz Agent" as the attributed source, and is nullable
because Phase 1 never populates it (no agents exist yet).
"""

from __future__ import annotations

import enum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Populated by future phases only — which agent(s) produced this
    # assistant message. Nullable + unused in Phase 1 by design.
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        preview = (self.content[:40] + "...") if len(self.content) > 40 else self.content
        return f"<Message id={self.id} role={self.role} content={preview!r}>"
