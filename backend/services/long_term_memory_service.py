"""
services/long_term_memory_service.py — Phase 4

WHY THIS FILE EXISTS
---------------------
Implements `memory/interfaces.py::LongTermMemory` for real. Long-term
memory is durable (`Memory` rows with `memory_type=LONG_TERM`, no
`expires_at`) AND semantically searchable — this service is what indexes a
memory into the dedicated memory FAISS index at write time, reusing Phase
3's `EmbeddingService` completely unmodified (per the Phase 4 brief's "Do
NOT duplicate embedding logic" instruction).

WHY INDEXING HAPPENS HERE, NOT IN MemorySearchService
------------------------------------------------------------
Writing and searching are different responsibilities even though they
share infrastructure: this service owns "is this memory durable and
findable," `services/memory_search_service.py` owns "given a query, which
memories match." Indexing at write time (rather than lazily at first
search) means a memory is searchable immediately, with no separate
"reindex" step — deliberately different from Phase 3's document pipeline,
where indexing was decoupled from upload for cost/latency reasons that
don't apply here (one short memory string embeds near-instantly, unlike a
whole document's chunk set).
"""

from __future__ import annotations

from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from memory.interfaces import LongTermMemory
from models.memory import Memory, MemoryType
from models.memory_embedding import MemoryEmbedding
from repositories.memory_embedding_repository import MemoryEmbeddingRepository
from repositories.memory_repository import MemoryRepository
from retrieval.embedder import EmbeddingService
from retrieval.vector_store import chunk_uuid_to_vector_id, get_memory_vector_store


class LongTermMemoryService(LongTermMemory):
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MemoryRepository(db)
        self.embedding_repo = MemoryEmbeddingRepository(db)
        self.embedding_service = EmbeddingService.get_instance()
        self.vector_store = get_memory_vector_store(dimension=self.embedding_service.dimension)

    # ------------------------------------------------------------------ #
    # memory/interfaces.py::BaseMemoryStore contract
    # ------------------------------------------------------------------ #
    def write(self, user_id: UUID, content: str, *, importance_score: float = 0.5, **scope) -> Memory:
        memory = Memory(
            user_id=user_id,
            memory_type=MemoryType.LONG_TERM,
            content=content,
            importance_score=importance_score,
            expires_at=None,  # long-term memory does not expire on a timer — see docs/Phase4.md Section 4
            conversation_id=scope.get("conversation_id"),
            document_id=scope.get("document_id"),
        )
        created = self.repo.create(memory)
        self._index_for_semantic_search(created)
        return created

    def read(self, user_id: UUID, **filters) -> list[Memory]:
        limit = filters.get("limit", 50)
        return self.repo.list_by_type(user_id, MemoryType.LONG_TERM, limit=limit)

    # ------------------------------------------------------------------ #
    # Update / delete — explicitly required by the Phase 4 brief
    # ------------------------------------------------------------------ #
    def update(self, memory_id: UUID, *, content: str | None = None, importance_score: float | None = None) -> Memory:
        memory = self.repo.get(memory_id)
        if memory is None:
            from core.exceptions import MemoryNotFoundError

            raise MemoryNotFoundError("Memory not found")

        content_changed = content is not None and content != memory.content
        if content is not None:
            memory.content = content
        if importance_score is not None:
            memory.importance_score = importance_score
        self.repo.commit_refresh(memory)

        if content_changed:
            # The old vector no longer represents this memory's content —
            # re-index rather than leaving a stale embedding searchable.
            self._remove_from_index(memory_id)
            self._index_for_semantic_search(memory)

        return memory

    def delete(self, memory_id: UUID) -> None:
        self._remove_from_index(memory_id)
        memory = self.repo.get(memory_id)
        if memory is not None:
            self.repo.delete(memory)

    # ------------------------------------------------------------------ #
    # Semantic indexing — reuses Phase 3's EmbeddingService/FAISSVectorStore unmodified
    # ------------------------------------------------------------------ #
    def _index_for_semantic_search(self, memory: Memory) -> None:
        vector = self.embedding_service.embed_query(memory.content)
        vector_id = chunk_uuid_to_vector_id(memory.id)  # same deterministic derivation Phase 3 uses for chunks

        self.vector_store.add_vectors(np.array([vector_id], dtype=np.int64), vector.reshape(1, -1))
        self.embedding_repo.create(
            MemoryEmbedding(
                memory_id=memory.id,
                vector_id=vector_id,
                embedding_model=getattr(self.embedding_service.backend, "model_name", "unknown"),
                dimension=self.embedding_service.dimension,
            )
        )
        self.vector_store.save()

    def _remove_from_index(self, memory_id: UUID) -> None:
        existing = self.embedding_repo.get_by_memory_id(memory_id)
        if existing is None:
            return
        self.vector_store.remove_vectors(np.array([existing.vector_id], dtype=np.int64))
        self.embedding_repo.delete_by_memory_id(memory_id)
        self.vector_store.save()
