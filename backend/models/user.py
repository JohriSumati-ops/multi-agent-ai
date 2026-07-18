"""
models/user.py

WHY THIS MODEL EXISTS
-----------------------
Every other table in the system (documents, conversations, learning
profile, memory) is scoped to a user. Without this table there is no
concept of "ownership" and no way to personalize anything.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
This is the aggregate root of the whole schema — relationships are declared
here (`back_populates`) so navigation is possible in both directions
(`user.documents`, `document.owner`) without repositories needing to write
manual joins for common access patterns.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
The Learning Profile and Memory models (Phase 5 in the roadmap, scaffolded
now) both hang off `user_id`. The future Supervisor Agent will use
`user_id` to scope every retrieval and memory read so one user's documents
never leak into another user's context.
"""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships — lazy="selectin" avoids the N+1 query problem for the
    # common case of loading a user alongside a small number of related rows,
    # without requiring every caller to remember to eager-load manually.
    documents: Mapped[list["Document"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
    learning_profile: Mapped["LearningProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    memory_entries: Mapped[list["Memory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience only
        return f"<User id={self.id} email={self.email!r}>"
