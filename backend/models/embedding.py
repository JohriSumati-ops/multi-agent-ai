"""
models/embedding.py — Phase 3

WHY THIS MODEL EXISTS
-----------------------
Architecture Section 5.2 anticipated this exact table: "Stores vector IDs
and metadata linking a chunk to its vector-store entry (the actual float
vectors live in FAISS; this table is the join/reference layer)." Phase 3
is the phase that makes that real.

The actual embedding vectors are NEVER stored in PostgreSQL — only in the
FAISS index (`retrieval/vector_store.py`). This table exists purely to
answer "which FAISS vector ID corresponds to this chunk" and the reverse,
"which chunk does this FAISS search result's vector ID correspond to."

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Keeping the relational database as the source of truth for *which* vectors
exist (even though it doesn't store their values) is what makes the vector
store swappable later — see Architecture Section 5.3's polyglot-persistence
rationale, exercised for real here for the first time.

HOW THIS PREPARES FOR PHASE 4+
-----------------------------------
`embedding_model` and `dimension` are stored per-row (not just globally)
so that a future model migration can identify and re-embed only the rows
using a stale model, rather than needing an all-or-nothing rebuild.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Embedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "embeddings"
    __table_args__ = (UniqueConstraint("chunk_id", name="uq_embeddings_chunk_id"),)

    chunk_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Denormalized for convenience: lets the retrieval repository filter or
    # delete-by-document without an extra join through document_chunks on
    # every query — the same denormalization tradeoff Phase 1's
    # LearningProfile made, documented there for the same reason.
    document_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # The integer ID this vector is stored under in the FAISS IndexIDMap —
    # see retrieval/vector_store.py's docstring for how this is derived
    # from `chunk_id` deterministically.
    vector_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)

    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)

    chunk: Mapped["DocumentChunk"] = relationship()
    document: Mapped["Document"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Embedding id={self.id} chunk_id={self.chunk_id} vector_id={self.vector_id}>"
