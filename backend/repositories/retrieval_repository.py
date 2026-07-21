"""
repositories/retrieval_repository.py — Phase 3

WHY THIS FILE EXISTS
---------------------
`SemanticSearchService` needs "search by vector, get back real chunk/
document data" as one operation, but that operation spans two entirely
different data stores: FAISS (the vectors) and PostgreSQL (everything
about what those vectors represent). This repository is the single
component that knows about both — composing `FAISSVectorStore.search()`
with `EmbeddingRepository`/`DocumentChunkRepository`/`DocumentRepository`
lookups — so `SemanticSearchService` itself never needs to import `faiss`
or know that a vector store exists at all.

This is the same Repository Pattern boundary Phase 1 established
(business logic depends on a repository interface, never on the storage
mechanism directly), extended here to a non-SQL store for the first time.
"""

from __future__ import annotations

from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from models.document import Document
from models.document_chunk import DocumentChunk
from repositories.document_chunk_repository import DocumentChunkRepository
from repositories.document_repository import DocumentRepository
from repositories.embedding_repository import EmbeddingRepository
from retrieval.vector_store import FAISSVectorStore


class RetrievalRepository:
    def __init__(self, db: Session, vector_store: FAISSVectorStore) -> None:
        self.db = db
        self.vector_store = vector_store
        self.embeddings = EmbeddingRepository(db)
        self.chunks = DocumentChunkRepository(db)
        self.documents = DocumentRepository(db)

    def vector_search(
        self, query_vector: np.ndarray, top_k: int, *, owner_id: UUID | None = None
    ) -> list[tuple[DocumentChunk, Document, float]]:
        """
        Runs a FAISS similarity search and resolves each hit back to its
        `DocumentChunk` and `Document` rows.

        `owner_id`, when provided, filters out results belonging to
        another user's documents — requested at a wider fan-out than
        `top_k` (see `_OVERFETCH_FACTOR`) so filtering doesn't silently
        shrink the result count below what the caller asked for whenever
        a user has few of their own documents mixed into a shared index.
        """
        overfetch_k = top_k * _OVERFETCH_FACTOR if owner_id else top_k
        scores, vector_ids = self.vector_store.search(query_vector, overfetch_k)
        if len(vector_ids) == 0:
            return []

        embeddings = self.embeddings.get_by_vector_ids([int(v) for v in vector_ids])
        embedding_by_vector_id = {e.vector_id: e for e in embeddings}

        results: list[tuple[DocumentChunk, Document, float]] = []
        for score, vector_id in zip(scores, vector_ids, strict=True):
            embedding = embedding_by_vector_id.get(int(vector_id))
            if embedding is None:
                # Stale FAISS entry with no matching DB row (e.g., the DB
                # row was deleted but the vector removal didn't happen for
                # some reason) — skip rather than error, since a single
                # dangling vector shouldn't fail the whole search.
                continue

            chunk = self.chunks.get(embedding.chunk_id)
            if chunk is None:
                continue
            document = self.documents.get(embedding.document_id)
            if document is None:
                continue
            if owner_id is not None and document.owner_id != owner_id:
                continue

            results.append((chunk, document, float(score)))
            if len(results) >= top_k:
                break

        return results

    def get_chunk_with_document(self, chunk_id: UUID) -> tuple[DocumentChunk, Document] | None:
        chunk = self.chunks.get(chunk_id)
        if chunk is None:
            return None
        document = self.documents.get(chunk.document_id)
        if document is None:
            return None
        return chunk, document

    def get_embedding_stats_for_document(self, document_id: UUID) -> dict:
        embeddings = self.embeddings.list_for_document(document_id)
        chunks = self.chunks.list_for_document(document_id)
        return {
            "chunk_count": len(chunks),
            "embedded_chunk_count": len(embeddings),
            "is_fully_embedded": len(embeddings) == len(chunks) and len(chunks) > 0,
        }


_OVERFETCH_FACTOR = 4
