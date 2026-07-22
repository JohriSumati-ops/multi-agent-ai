"""
repositories/memory_embedding_repository.py — Phase 4

Mirrors repositories/embedding_repository.py exactly, for the memory
FAISS index's mapping table. See models/memory_embedding.py's docstring
for why this is a separate table/repository rather than reusing Phase 3's.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.memory_embedding import MemoryEmbedding
from repositories.base_repository import BaseRepository


class MemoryEmbeddingRepository(BaseRepository[MemoryEmbedding]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, MemoryEmbedding)

    def get_by_memory_id(self, memory_id: UUID) -> MemoryEmbedding | None:
        stmt = select(MemoryEmbedding).where(MemoryEmbedding.memory_id == memory_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_vector_ids(self, vector_ids: list[int]) -> list[MemoryEmbedding]:
        if not vector_ids:
            return []
        stmt = select(MemoryEmbedding).where(MemoryEmbedding.vector_id.in_(vector_ids))
        return list(self.db.execute(stmt).scalars().all())

    def delete_by_memory_id(self, memory_id: UUID) -> None:
        stmt = delete(MemoryEmbedding).where(MemoryEmbedding.memory_id == memory_id)
        self.db.execute(stmt)
        self.db.commit()

    def bulk_create(self, embeddings: list[MemoryEmbedding]) -> list[MemoryEmbedding]:
        self.db.add_all(embeddings)
        self.db.commit()
        for e in embeddings:
            self.db.refresh(e)
        return embeddings
