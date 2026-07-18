"""
models/document.py

WHY THIS MODEL EXISTS
-----------------------
Phase 1 has no PDF parsing, chunking, or embedding — but the frontend's
Document Library page and the eventual ingestion pipeline both need a
stable place to record "a file was uploaded, here is its metadata, here is
its processing status." This table is that anchor.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Modeling a resource's lifecycle explicitly via a status enum
(`DocumentStatus`) rather than a set of boolean flags (`is_parsed`,
`is_embedded`, ...) avoids invalid state combinations and makes the
ingestion pipeline's state machine (Section 7.1 of the architecture)
directly visible in the schema.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
The PDF Parsing Agent will update `status` to PARSING → PARSED, the
Embedding Agent will move it to EMBEDDING → READY. `document_chunks`,
`embeddings`, and `knowledge_graph_nodes` (all introduced in Phase 1's
successor phases) will each carry a foreign key back to `documents.id`.
"""

from __future__ import annotations

import enum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentStatus(str, enum.Enum):
    """
    Tracks a document's position in the ingestion pipeline described in
    Architecture Section 7.1. Only UPLOADED is reachable in Phase 1 since
    no processing agents exist yet — the remaining values are defined now
    so the column type never needs to change later.
    """

    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    LECTURE_NOTES = "lecture_notes"
    RESEARCH_PAPER = "research_paper"
    CODING_NOTES = "coding_notes"
    OTHER = "other"


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documents"

    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    document_type: Mapped[DocumentType] = mapped_column(
        default=DocumentType.OTHER, nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        default=DocumentStatus.UPLOADED, nullable=False, index=True
    )

    # Free-form subject/topic tag, to be populated by the future Metadata
    # Agent. Nullable because Phase 1 never sets it.
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="documents")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Document id={self.id} title={self.title!r} status={self.status}>"
