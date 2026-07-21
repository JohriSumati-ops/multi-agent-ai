"""
services/semantic_search_service.py — Phase 3

WHY THIS FILE EXISTS
---------------------
The single orchestration point for everything the retrieval API needs:
embedding a query, searching FAISS via `RetrievalRepository`, ranking
results, and the index-management operations (reindex/rebuild) the API
also exposes. Exactly the Service Layer role Phase 1 established — this
file has no SQL and no FAISS calls of its own, only calls into the
repositories that do.

DESIGN DECISION: EMBEDDING IS NOT AUTOMATIC ON UPLOAD
-----------------------------------------------------------
Phase 2's `POST /documents/upload` pipeline ends at `DocumentStatus.CHUNKED`
and is deliberately left untouched by Phase 3 — it does not automatically
progress to `EMBEDDING`/`READY`. This was a considered choice, not an
oversight: automatically embedding on every upload would (a) block the
upload response on a potentially slow model call, and (b) change
`test_documents.py`'s existing, passing assertions about post-upload
status, which the Phase 3 brief explicitly requires to keep passing.
Instead, embedding is an explicit action — `POST /retrieval/reindex` for
one document, or `POST /retrieval/rebuild` for the whole corpus — which is
also a more realistic production shape (ingestion and indexing are
commonly decoupled, retryable stages). See docs/Phase3.md's "Implementation
Verification Notes" for the full writeup of this tradeoff.

MULTI-TENANCY CAVEAT (documented, not silently ignored)
--------------------------------------------------------------
The FAISS index is a single, shared, process-wide store — not one index
per user. `search()`/`find_similar()` enforce per-user ownership by
overfetching and filtering in `RetrievalRepository` (never returning
another user's chunks), and `reindex_document()` is ownership-checked
per-document. `rebuild_index()`, however, operates on the ENTIRE index
across all users — there is no admin/role system yet to restrict it to a
privileged caller, matching this project's current "personal study tool,
no RBAC" scope (Phase 1 never built roles either). This is flagged
explicitly here and in docs/Phase3.md as a known limitation to revisit
before any multi-user production deployment.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from agents.embedding_agent import ChunkEmbeddingInput, EmbeddingAgent
from core.agent_bus import TaskContext
from core.exceptions import DocumentNotEmbeddableError, NotFoundError
from core.logging import get_logger
from models.agent_execution_log import AgentExecutionLog, AgentExecutionStatus
from models.document import DocumentStatus
from models.document_chunk import DocumentChunk
from models.embedding import Embedding
from repositories.agent_execution_log_repository import AgentExecutionLogRepository
from repositories.document_chunk_repository import DocumentChunkRepository
from repositories.document_repository import DocumentRepository
from repositories.embedding_repository import EmbeddingRepository
from repositories.retrieval_repository import RetrievalRepository
from retrieval.embedder import EmbeddingService
from retrieval.ranking import RetrievalCandidate, RankedResult, rank_candidates
from retrieval.vector_store import chunk_uuid_to_vector_id, get_vector_store

logger = get_logger("app")

_EMBEDDABLE_STATUSES = {DocumentStatus.CHUNKED, DocumentStatus.EMBEDDING, DocumentStatus.READY}


class SemanticSearchService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding_service = EmbeddingService.get_instance()
        self.vector_store = get_vector_store(dimension=self.embedding_service.dimension)
        self.retrieval_repo = RetrievalRepository(db, self.vector_store)
        self.embeddings = EmbeddingRepository(db)
        self.chunks = DocumentChunkRepository(db)
        self.documents = DocumentRepository(db)
        self.agent_logs = AgentExecutionLogRepository(db)

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    def search(
        self,
        *,
        query: str,
        top_k: int,
        similarity_threshold: float,
        owner_id: UUID,
        document_id: UUID | None = None,
    ) -> list[RankedResult]:
        query_vector = self.embedding_service.embed_query(query)
        overfetch = top_k * 4  # generous fan-out so document_id filtering doesn't starve results
        raw_hits = self.retrieval_repo.vector_search(query_vector, overfetch, owner_id=owner_id)

        candidates = [
            RetrievalCandidate(
                chunk_id=str(chunk.id),
                document_id=str(document.id),
                document_title=document.title,
                chunk_text=chunk.chunk_text,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                similarity_score=score,
            )
            for chunk, document, score in raw_hits
            if document_id is None or str(document.id) == str(document_id)
        ]
        return rank_candidates(candidates, top_k=top_k, similarity_threshold=similarity_threshold)

    def find_similar_to_chunk(
        self, *, chunk_id: UUID, top_k: int, similarity_threshold: float, owner_id: UUID
    ) -> list[RankedResult]:
        chunk_and_doc = self.retrieval_repo.get_chunk_with_document(chunk_id)
        if chunk_and_doc is None:
            raise NotFoundError("Chunk not found")
        chunk, document = chunk_and_doc
        if document.owner_id != owner_id:
            raise NotFoundError("Chunk not found")

        # No raw vector is persisted anywhere outside FAISS itself, so the
        # simplest correct way to get "this chunk's vector" is to re-embed
        # its text — the embedding cache (retrieval/embedder.py) makes this
        # effectively free when the chunk was embedded recently.
        query_vector = self.embedding_service.embed_query(chunk.chunk_text)
        overfetch = (top_k + 1) * 4
        raw_hits = self.retrieval_repo.vector_search(query_vector, overfetch, owner_id=owner_id)

        candidates = [
            RetrievalCandidate(
                chunk_id=str(c.id),
                document_id=str(d.id),
                document_title=d.title,
                chunk_text=c.chunk_text,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                similarity_score=score,
            )
            for c, d, score in raw_hits
            if str(c.id) != str(chunk_id)  # exclude the query chunk itself
        ]
        return rank_candidates(candidates, top_k=top_k, similarity_threshold=similarity_threshold)

    # ------------------------------------------------------------------ #
    # Status / metadata reads
    # ------------------------------------------------------------------ #
    def get_document_retrieval_status(self, document_id: UUID) -> dict:
        document = self.documents.get(document_id)
        if document is None:
            raise NotFoundError("Document not found")
        stats = self.retrieval_repo.get_embedding_stats_for_document(document_id)
        return {"document": document, **stats}

    def get_chunk_vector_info(self, chunk_id: UUID) -> Embedding:
        embedding = self.embeddings.get_by_chunk_id(chunk_id)
        if embedding is None:
            raise NotFoundError("No embedding exists for this chunk yet — has it been indexed?")
        return embedding

    # ------------------------------------------------------------------ #
    # Index management: reindex (one document) / rebuild (entire index)
    # ------------------------------------------------------------------ #
    def reindex_document(self, document_id: UUID, owner_id: UUID) -> int:
        """
        (Re-)embeds every chunk of one document and adds/updates its
        vectors in the FAISS index. Returns the number of chunks embedded.
        Idempotent: existing vectors for this document are removed first,
        so calling this twice never produces duplicate index entries.
        """
        document = self.documents.get(document_id)
        if document is None or document.owner_id != owner_id:
            raise NotFoundError("Document not found")
        if document.status not in _EMBEDDABLE_STATUSES:
            raise DocumentNotEmbeddableError(
                f"Document status is '{document.status.value}' — it must reach 'chunked' "
                "before it can be indexed (has the Phase 2 pipeline finished?)."
            )

        chunks = self.chunks.list_for_document(document_id)
        if not chunks:
            document.status = DocumentStatus.CHUNKED
            self.documents.commit_refresh(document)
            return 0

        document.status = DocumentStatus.EMBEDDING
        self.documents.commit_refresh(document)

        # Remove any prior vectors for this document (both FAISS and the
        # DB mapping) so re-indexing is idempotent rather than additive.
        existing = self.embeddings.list_for_document(document_id)
        if existing:
            import numpy as np

            stale_vector_ids = np.array(
                [chunk_uuid_to_vector_id(e.chunk_id) for e in existing], dtype=np.int64
            )
            self.vector_store.remove_vectors(stale_vector_ids)
            self.embeddings.delete_for_document(document_id)

        chunk_count = self._embed_and_persist(chunks, document_id)

        document.status = DocumentStatus.READY
        self.documents.commit_refresh(document)
        self.vector_store.save()

        logger.info("Reindexed document %s: %d chunks embedded", document_id, chunk_count)
        return chunk_count

    def rebuild_index(self) -> tuple[int, int]:
        """
        Wipes the ENTIRE FAISS index and re-embeds every eligible
        document's chunks from scratch — the corruption-recovery /
        model-migration path referenced in retrieval/vector_store.py's
        docstring. See this module's docstring for the multi-tenancy
        caveat: this operates across ALL users' documents.

        Returns (documents_processed, total_chunks_embedded).
        """
        self.vector_store.rebuild_empty()
        self.embeddings.db.query(Embedding).delete()
        self.embeddings.db.commit()

        documents_processed = 0
        total_chunks = 0

        all_chunked_or_ready = [
            d
            for d in self.documents.list(limit=100_000)
            if d.status in _EMBEDDABLE_STATUSES
        ]
        for document in all_chunked_or_ready:
            chunks = self.chunks.list_for_document(document.id)
            if not chunks:
                continue
            document.status = DocumentStatus.EMBEDDING
            self.documents.commit_refresh(document)

            count = self._embed_and_persist(chunks, document.id)
            total_chunks += count
            documents_processed += 1

            document.status = DocumentStatus.READY
            self.documents.commit_refresh(document)

        self.vector_store.save()
        logger.info(
            "Rebuilt FAISS index: %d documents, %d chunks embedded", documents_processed, total_chunks
        )
        return documents_processed, total_chunks

    # ------------------------------------------------------------------ #
    # Shared embedding + persistence logic (used by both reindex and rebuild)
    # ------------------------------------------------------------------ #
    def _embed_and_persist(self, chunks: list[DocumentChunk], document_id: UUID) -> int:
        context = TaskContext(original_query="", active_document_ids=[str(document_id)])
        context.intermediate_results["chunks_to_embed"] = [
            ChunkEmbeddingInput(chunk_id=str(c.id), text=c.chunk_text) for c in chunks
        ]

        agent_result = EmbeddingAgent().run(context)

        self.agent_logs.create(
            AgentExecutionLog(
                task_id=str(uuid4()),
                agent_name=agent_result.agent_name,
                status=AgentExecutionStatus.SUCCESS if agent_result.success else AgentExecutionStatus.FAILED,
                latency_ms=agent_result.execution_time_ms,
                error_message=agent_result.error_message,
                extra_metadata={"document_id": str(document_id), "chunk_count": len(chunks)},
            )
        )

        if not agent_result.success:
            raise DocumentNotEmbeddableError(agent_result.error_message or "Embedding failed")

        embedding_results = agent_result.output
        vector_ids = [chunk_uuid_to_vector_id(c.id) for c in chunks]
        vectors = [r.vector for r in embedding_results]

        import numpy as np

        self.vector_store.add_vectors(np.array(vector_ids, dtype=np.int64), np.stack(vectors))

        embedding_rows = [
            Embedding(
                chunk_id=chunk.id,
                document_id=document_id,
                vector_id=vector_id,
                embedding_model=result.model_name,
                dimension=result.dimension,
            )
            for chunk, vector_id, result in zip(chunks, vector_ids, embedding_results, strict=True)
        ]
        self.embeddings.bulk_create(embedding_rows)

        return len(embedding_rows)
