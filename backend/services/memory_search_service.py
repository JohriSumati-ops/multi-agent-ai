"""
services/memory_search_service.py — Phase 4

WHY THIS FILE EXISTS
---------------------
Semantic search over memory, architecturally identical to Phase 3's
`SemanticSearchService` on purpose (see docs/Phase4.md Section 5) —
embed the query, search the (memory-specific) FAISS index, resolve hits
back to `Memory` rows, rank with explainability. Reuses
`retrieval/ranking.py` unmodified by mapping `Memory` rows into the same
`RetrievalCandidate` shape Phase 3's document search uses, rather than
inventing a parallel ranking implementation.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from models.memory import Memory
from repositories.memory_access_log_repository import MemoryAccessLogRepository
from repositories.memory_embedding_repository import MemoryEmbeddingRepository
from repositories.memory_repository import MemoryRepository
from models.memory_access_log import MemoryAccessType
from retrieval.embedder import EmbeddingService
from retrieval.ranking import RankedResult, RetrievalCandidate, rank_candidates
from retrieval.vector_store import get_memory_vector_store


class MemorySearchService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.memory_repo = MemoryRepository(db)
        self.embedding_repo = MemoryEmbeddingRepository(db)
        self.access_log_repo = MemoryAccessLogRepository(db)
        self.embedding_service = EmbeddingService.get_instance()
        self.vector_store = get_memory_vector_store(dimension=self.embedding_service.dimension)

    def search(
        self,
        *,
        query: str,
        user_id: UUID,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> list[RankedResult]:
        """
        Embeds `query`, searches the memory FAISS index, resolves hits back
        to `Memory` rows (scoped to `user_id` — never another user's
        memory), and returns explainable ranked results. Every returned
        memory also gets a `SEARCH_HIT` row in `MemoryAccessLog` (see
        docs/Phase4.md Section 4's access-tracking rationale).
        """
        query_vector = self.embedding_service.embed_query(query)
        overfetch = top_k * 4
        scores, vector_ids = self.vector_store.search(query_vector, overfetch)
        if len(vector_ids) == 0:
            return []

        embeddings = self.embedding_repo.get_by_vector_ids([int(v) for v in vector_ids])
        embedding_by_vector_id = {e.vector_id: e for e in embeddings}

        memory_ids = [e.memory_id for e in embeddings]
        memories_by_id = {m.id: m for m in self.memory_repo.get_by_ids(memory_ids)}

        candidates: list[RetrievalCandidate] = []
        score_by_memory_id: dict[UUID, float] = {}
        for score, vector_id in zip(scores, vector_ids, strict=True):
            embedding = embedding_by_vector_id.get(int(vector_id))
            if embedding is None:
                continue
            memory = memories_by_id.get(embedding.memory_id)
            if memory is None or memory.user_id != user_id:
                continue  # ownership check — never return another user's memory

            score_by_memory_id[memory.id] = float(score)
            candidates.append(
                RetrievalCandidate(
                    chunk_id=str(memory.id),  # reusing ranking.py's field names — a "memory" plays the role of a "chunk" here
                    document_id=str(memory.id),
                    document_title=f"[{memory.memory_type.value}] memory",
                    chunk_text=memory.content,
                    page_number=None,
                    chunk_index=0,
                    similarity_score=float(score),
                )
            )

        results = rank_candidates(candidates, top_k=top_k, similarity_threshold=similarity_threshold)

        for result in results:
            self.access_log_repo.log_access(UUID(result.chunk_id), user_id, MemoryAccessType.SEARCH_HIT)

        return results

    def find_similar_to_memory(
        self, *, memory_id: UUID, user_id: UUID, top_k: int = 5, similarity_threshold: float = 0.0
    ) -> list[RankedResult]:
        memory = self.memory_repo.get(memory_id)
        if memory is None or memory.user_id != user_id:
            from core.exceptions import MemoryNotFoundError

            raise MemoryNotFoundError("Memory not found")

        results = self.search(
            query=memory.content, user_id=user_id, top_k=top_k + 1, similarity_threshold=similarity_threshold
        )
        return [r for r in results if r.chunk_id != str(memory_id)][:top_k]
