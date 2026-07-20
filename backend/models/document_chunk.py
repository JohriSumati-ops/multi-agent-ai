"""
models/document_chunk.py — Phase 2

WHY THIS MODEL EXISTS
-----------------------
Architecture Section 5.2 already anticipated a `document_chunks` table
("retrieval operates on chunks, not whole documents"). Phase 2 is the phase
that actually produces chunks — via the Chunking Engine
(`retrieval/chunker.py`) — so this is the storage target for that output.

Deliberately NOT storing an embedding vector here (that's Phase 3's job,
via a separate `embeddings` reference table pointing at a vector store).
This table stores exactly what Phase 2 produces: text + structural/
positional metadata, nothing AI-generated.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
`chunk_index` (ordering within a document) is stored explicitly rather than
relied upon implicitly, because chunking strategies (sentence vs. sliding
window) don't guarantee chunks are contiguous or non-overlapping — explicit
ordering avoids relying on database insertion order, which SQL never
guarantees on its own.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Phase 3's Embedding Agent will read every chunk for a document via
`DocumentChunkRepository.list_for_document`, embed `chunk_text`, and write
a row into a future `embeddings` table referencing `DocumentChunk.id`. The
Retrieval Agent's search results are, at the storage level, just a ranked
subset of this table's rows.
"""

from __future__ import annotations

import enum

from sqlalchemy import Float, ForeignKey, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChunkingStrategy(str, enum.Enum):
    """Which of the Chunking Engine's four strategies produced this chunk."""

    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    SLIDING_WINDOW = "sliding_window"


class DocumentChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_chunks"

    document_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Ordering within the document — see docstring above for why this is
    # explicit rather than inferred from insertion order.
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Which page this chunk came from, when the source format has pages
    # (PDF). Null for formats without pagination (txt, md).
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Character offsets into the document's full cleaned text — lets a
    # future citation feature highlight exactly where a chunk came from.
    start_position: Mapped[int] = mapped_column(Integer, nullable=False)
    end_position: Mapped[int] = mapped_column(Integer, nullable=False)

    # Approximate token count (whitespace-based in Phase 2 — see
    # document_processing/nlp_preprocessor.py's docstring for why a real
    # tokenizer is deliberately deferred to Phase 3).
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)

    chunking_strategy: Mapped[ChunkingStrategy] = mapped_column(nullable=False, index=True)

    # Escape hatch for strategy-specific extras (e.g., sliding window's
    # overlap size, paragraph chunking's source paragraph index) without a
    # column per strategy.
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="chunks")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<DocumentChunk id={self.id} document_id={self.document_id} "
            f"index={self.chunk_index} strategy={self.chunking_strategy}>"
        )
