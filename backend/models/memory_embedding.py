"""
models/memory_embedding.py — Phase 4

WHY THIS MODEL EXISTS
-----------------------
Mirrors `models/embedding.py` exactly, but maps `Memory` rows to FAISS
vector IDs instead of `DocumentChunk` rows. Kept as a genuinely separate
table (not a reused/overloaded `Embedding` row) because a memory's vector
lives in a *different* FAISS index from a document chunk's vector — see
docs/Phase4.md Section 6, design decision #2, for why the two indexes are
kept separate. Reusing one join table for two different indexes would
require an extra "which index does this row belong to" column and
special-cased queries everywhere; two small, single-purpose tables are
simpler and match this project's established pattern of one mapping table
per FAISS index.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MemoryEmbedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "memory_embeddings"
    __table_args__ = (UniqueConstraint("memory_id", name="uq_memory_embeddings_memory_id"),)

    memory_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memory.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vector_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)

    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)

    memory: Mapped["Memory"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MemoryEmbedding id={self.id} memory_id={self.memory_id} vector_id={self.vector_id}>"
