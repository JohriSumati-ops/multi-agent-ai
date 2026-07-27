"""
models/research_response.py — Phase 6

WHY THIS MODEL EXISTS
-----------------------
Persists the final, validated output of the reasoning pipeline (Section 12
of docs/Phase6.md) — the answer, its sources, confidence, and the
explainability metadata this phase's brief requires every response to
include. `POST /research/explain` (see api/routes/research.py) reads this
table to reconstruct a past response's full trace, which is why
`context_sources`, `memory_references`, and `retrieved_chunk_ids` are
stored as JSON here rather than only existing transiently in the response
object returned at request time.
"""

from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResearchResponse(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "research_responses"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)

    sources_used: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    memory_references: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    retrieved_chunk_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    prompt_tokens: Mapped[int | None] = mapped_column(nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)

    # Full DecisionTrace / Explanation payload, stored verbatim as JSON so
    # /research/explain can reconstruct it without re-deriving anything —
    # the same "store the JSON, don't re-derive" rationale
    # models/orchestration_event.py gave for its payload column in Phase 5.
    explainability_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ResearchResponse id={self.id} user_id={self.user_id} confidence={self.confidence}>"
