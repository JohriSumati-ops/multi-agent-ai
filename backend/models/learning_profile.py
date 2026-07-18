"""
models/learning_profile.py

WHY THIS MODEL EXISTS
-----------------------
Personalization requires a durable, per-user summary of learning state that
is cheap to read on every Dashboard load. Recomputing "weak topics" or
"quiz accuracy" from raw quiz_history on every page view (once that table
exists) would be wasteful — this table is the materialized, continuously
updated summary, exactly as described in Architecture Section 5.2's
`study_progress` rationale (renamed/expanded here to `LearningProfile` per
the Phase 1 requirements).

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Denormalization as a deliberate, documented performance decision — this
table duplicates information derivable from other tables (once quiz history
exists) in exchange for O(1) dashboard reads instead of O(n) aggregation
queries. The tradeoff (write-side complexity to keep it in sync) is
accepted because reads vastly outnumber writes for this data.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
The Gap Analysis Agent (Phase 5) will read `weak_topics`/`strong_topics`.
The Recommendation Agent will read `preferred_difficulty` to calibrate
question generation. The Quiz Agent will update `quiz_accuracy` and
`revision_count` after every quiz attempt.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LearningProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "learning_profiles"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one profile per user
        index=True,
    )

    # Topic names, not foreign keys to knowledge_graph_nodes yet — that
    # table doesn't exist until Phase 4. Stored as JSON string lists now
    # (portable across Postgres and SQLite); migrating to a proper
    # many-to-many against knowledge graph nodes is a contained schema
    # change when that phase arrives.
    weak_topics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    strong_topics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    quiz_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revision_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    learning_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    preferred_difficulty: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(50), default="en", nullable=False)

    last_activity_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Escape hatch for future personalization signals we haven't
    # anticipated yet (e.g., study-session-length preference), without
    # requiring a migration for every new small preference. JSON (not
    # Postgres-only JSONB) so the same model works against SQLite in tests.
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped["User"] = relationship(back_populates="learning_profile")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LearningProfile user_id={self.user_id} accuracy={self.quiz_accuracy}>"
