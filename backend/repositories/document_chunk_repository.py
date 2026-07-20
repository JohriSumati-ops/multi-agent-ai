"""
repositories/document_chunk_repository.py
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.document_chunk import DocumentChunk
from repositories.base_repository import BaseRepository


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, DocumentChunk)

    def list_for_document(self, document_id: UUID) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def bulk_create(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """
        Insert many chunks in one transaction — used by the document
        processing pipeline, which produces all of a document's chunks in
        one pass rather than one at a time.
        """
        self.db.add_all(chunks)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return chunks

    def delete_for_document(self, document_id: UUID) -> None:
        """
        Used when reprocessing a document (e.g., re-chunking with a
        different strategy) so stale chunks from a previous run aren't
        left behind alongside the new ones.
        """
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        self.db.execute(stmt)
        self.db.commit()
