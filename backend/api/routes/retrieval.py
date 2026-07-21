"""
api/routes/retrieval.py — Phase 3

WHY THIS FILE EXISTS
---------------------
The HTTP surface for the Semantic Retrieval Layer. Per the "routers are
transport-only" rule (Phase 1), every handler here does nothing but read
the request, call `SemanticSearchService`, and shape the response — all
embedding, vector search, ranking, and index-management logic lives in the
service and the modules it calls.

All routes require authentication and enforce per-user ownership (see
`services/semantic_search_service.py`'s multi-tenancy caveat for the one
documented exception: `/rebuild` currently operates across all users,
since no role/permission system exists yet).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from api.deps import CurrentUser, SemanticSearchServiceDep
from schemas.base import APIResponse
from schemas.retrieval import (
    ChunkVectorInfo,
    DocumentRetrievalStatus,
    RankedResultOut,
    RebuildResponse,
    ReindexResponse,
    SearchRequest,
    SearchResponse,
    SimilarChunkRequest,
)

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=APIResponse[SearchResponse])
def search(
    payload: SearchRequest, service: SemanticSearchServiceDep, user: CurrentUser
) -> APIResponse[SearchResponse]:
    document_id = UUID(payload.document_id) if payload.document_id else None
    results = service.search(
        query=payload.query,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
        owner_id=user.id,
        document_id=document_id,
    )
    response = SearchResponse(
        query=payload.query,
        result_count=len(results),
        results=[RankedResultOut(**r.__dict__) for r in results],
    )
    return APIResponse[SearchResponse](success=True, data=response)


@router.post("/similar", response_model=APIResponse[SearchResponse])
def find_similar(
    payload: SimilarChunkRequest, service: SemanticSearchServiceDep, user: CurrentUser
) -> APIResponse[SearchResponse]:
    results = service.find_similar_to_chunk(
        chunk_id=UUID(payload.chunk_id),
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
        owner_id=user.id,
    )
    response = SearchResponse(
        query=f"[similar to chunk {payload.chunk_id}]",
        result_count=len(results),
        results=[RankedResultOut(**r.__dict__) for r in results],
    )
    return APIResponse[SearchResponse](success=True, data=response)


@router.get("/document/{document_id}", response_model=APIResponse[DocumentRetrievalStatus])
def get_document_retrieval_status(
    document_id: UUID, service: SemanticSearchServiceDep, user: CurrentUser
) -> APIResponse[DocumentRetrievalStatus]:
    from core.exceptions import NotFoundError

    result = service.get_document_retrieval_status(document_id)
    document = result["document"]
    if document.owner_id != user.id:
        raise NotFoundError("Document not found")

    return APIResponse[DocumentRetrievalStatus](
        success=True,
        data=DocumentRetrievalStatus(
            document_id=str(document.id),
            title=document.title,
            status=document.status.value,
            chunk_count=result["chunk_count"],
            embedded_chunk_count=result["embedded_chunk_count"],
            is_fully_embedded=result["is_fully_embedded"],
        ),
    )


@router.get("/chunks/{chunk_id}", response_model=APIResponse[ChunkVectorInfo])
def get_chunk_vector_info(
    chunk_id: UUID, service: SemanticSearchServiceDep, user: CurrentUser
) -> APIResponse[ChunkVectorInfo]:
    from core.exceptions import NotFoundError

    chunk_and_doc = service.retrieval_repo.get_chunk_with_document(chunk_id)
    if chunk_and_doc is None or chunk_and_doc[1].owner_id != user.id:
        raise NotFoundError("Chunk not found")

    embedding = service.get_chunk_vector_info(chunk_id)
    return APIResponse[ChunkVectorInfo](
        success=True,
        data=ChunkVectorInfo(
            chunk_id=str(embedding.chunk_id),
            document_id=str(embedding.document_id),
            vector_id=embedding.vector_id,
            embedding_model=embedding.embedding_model,
            dimension=embedding.dimension,
        ),
    )


@router.post("/reindex", response_model=APIResponse[ReindexResponse])
def reindex_document(
    document_id: UUID, service: SemanticSearchServiceDep, user: CurrentUser
) -> APIResponse[ReindexResponse]:
    chunk_count = service.reindex_document(document_id, owner_id=user.id)
    return APIResponse[ReindexResponse](
        success=True,
        data=ReindexResponse(document_id=str(document_id), chunks_embedded=chunk_count, status="ready"),
    )


@router.post("/rebuild", response_model=APIResponse[RebuildResponse])
def rebuild_index(service: SemanticSearchServiceDep, user: CurrentUser) -> APIResponse[RebuildResponse]:
    # See services/semantic_search_service.py's multi-tenancy caveat:
    # this rebuilds the ENTIRE index across all users, not just the
    # caller's own documents — there is no role system yet to restrict it
    # further. Authentication is still required (CurrentUser), just not
    # per-owner scoping.
    documents_processed, chunks_embedded = service.rebuild_index()
    return APIResponse[RebuildResponse](
        success=True,
        data=RebuildResponse(
            documents_processed=documents_processed,
            chunks_embedded=chunks_embedded,
            vectors_in_index=service.vector_store.ntotal,
        ),
    )
