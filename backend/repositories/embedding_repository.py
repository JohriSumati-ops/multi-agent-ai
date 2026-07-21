"""
repositories/embedding_repository.py — Phase 3

Plain CRUD over the `embeddings` table — pure Repository Pattern, exactly
like every repository since Phase 1. FAISS-specific logic never appears
here; this file only knows SQL.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.embedding import Embedding
from repositories.base_repository import BaseRepository


class EmbeddingRepository(BaseRepository[Embedding]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Embedding)

    def get_by_chunk_id(self, chunk_id: UUID) -> Embedding | None:
        stmt = select(Embedding).where(Embedding.chunk_id == chunk_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_vector_ids(self, vector_ids: list[int]) -> list[Embedding]:
        """Bulk lookup used by RetrievalRepository to resolve FAISS search hits."""
        if not vector_ids:
            return []
        stmt = select(Embedding).where(Embedding.vector_id.in_(vector_ids))
        return list(self.db.execute(stmt).scalars().all())

    def list_for_document(self, document_id: UUID) -> list[Embedding]:
        stmt = select(Embedding).where(Embedding.document_id == document_id)
        return list(self.db.execute(stmt).scalars().all())

    def delete_for_document(self, document_id: UUID) -> None:
        stmt = delete(Embedding).where(Embedding.document_id == document_id)
        self.db.execute(stmt)
        self.db.commit()

    def bulk_create(self, embeddings: list[Embedding]) -> list[Embedding]:
        self.db.add_all(embeddings)
        self.db.commit()
        for e in embeddings:
            self.db.refresh(e)
        return embeddings
