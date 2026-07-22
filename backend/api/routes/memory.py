"""
api/routes/memory.py — Phase 4

WHY THIS FILE EXISTS
---------------------
The HTTP surface for the Memory System. Per the "routers are
transport-only" rule established in Phase 1, every handler here does
nothing but read the request, call `MemoryManager` (the facade — see
services/memory_manager.py), and shape the response.

All routes require authentication and are scoped to the current user —
memory is inherently personal, more so than documents (Phase 2) or
retrieval (Phase 3), so there is no equivalent here to Phase 3's
documented `/retrieval/rebuild` multi-tenancy caveat: every operation in
this file is already user-scoped by construction.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from api.deps import CurrentUser, MemoryManagerDep
from models.memory import MemoryType
from schemas.base import APIResponse
from schemas.memory_api import (
    ClearMemoryResponse,
    DeleteHistoryResponse,
    MemoryRecordOut,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResultOut,
    MemoryStatisticsResponse,
    MemoryStoreRequest,
    PruneResponse,
    SessionStateResponse,
)

router = APIRouter(prefix="/memory", tags=["memory"])


def _to_memory_record_out(memory) -> MemoryRecordOut:
    return MemoryRecordOut(
        id=memory.id,
        user_id=memory.user_id,
        memory_type=memory.memory_type,
        content=memory.content,
        importance_score=memory.importance_score,
        expires_at=memory.expires_at,
        conversation_id=memory.conversation_id,
        document_id=memory.document_id,
        created_at=memory.created_at,
    )


@router.post("/store", response_model=APIResponse[MemoryRecordOut], status_code=201)
def store_memory(
    payload: MemoryStoreRequest, manager: MemoryManagerDep, user: CurrentUser
) -> APIResponse[MemoryRecordOut]:
    memory = manager.remember(
        user.id,
        payload.content,
        persist_long_term=payload.persist_long_term,
        importance_score=payload.importance_score,
        conversation_id=payload.conversation_id,
        document_id=payload.document_id,
    )
    return APIResponse[MemoryRecordOut](success=True, data=_to_memory_record_out(memory))


@router.get("/session", response_model=APIResponse[SessionStateResponse])
def get_session(
    manager: MemoryManagerDep, user: CurrentUser, session_id: str = Query(...)
) -> APIResponse[SessionStateResponse]:
    state = manager.get_session_state(session_id, user.id)
    return APIResponse[SessionStateResponse](
        success=True, data=SessionStateResponse(session_id=session_id, state=state)
    )


@router.get("/history", response_model=APIResponse[list[MemoryRecordOut]])
def get_history(
    manager: MemoryManagerDep,
    user: CurrentUser,
    memory_type: MemoryType | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> APIResponse[list[MemoryRecordOut]]:
    memories = manager.get_history(user.id, memory_type=memory_type, limit=limit)
    return APIResponse[list[MemoryRecordOut]](success=True, data=[_to_memory_record_out(m) for m in memories])


@router.get("/recent", response_model=APIResponse[list[MemoryRecordOut]])
def get_recent(
    manager: MemoryManagerDep, user: CurrentUser, limit: int = Query(default=10, ge=1, le=100)
) -> APIResponse[list[MemoryRecordOut]]:
    memories = manager.get_recent(user.id, limit=limit)
    return APIResponse[list[MemoryRecordOut]](success=True, data=[_to_memory_record_out(m) for m in memories])


@router.get("/search", response_model=APIResponse[MemorySearchResponse])
def search_memory(
    manager: MemoryManagerDep,
    user: CurrentUser,
    query: str = Query(..., min_length=1, max_length=2000),
    top_k: int = Query(default=5, ge=1, le=50),
    similarity_threshold: float = Query(default=0.3, ge=-1.0, le=1.0),
) -> APIResponse[MemorySearchResponse]:
    # Validated through the same schema used for potential future POST
    # support, even though this endpoint accepts query params per the
    # Phase 4 spec's explicit "GET /memory/search" — keeps validation
    # rules (length bounds, top_k range) defined in exactly one place.
    validated = MemorySearchRequest(query=query, top_k=top_k, similarity_threshold=similarity_threshold)

    results = manager.search(
        query=validated.query, user_id=user.id, top_k=validated.top_k, similarity_threshold=validated.similarity_threshold
    )
    response = MemorySearchResponse(
        query=validated.query,
        result_count=len(results),
        results=[
            MemorySearchResultOut(
                rank=r.rank,
                memory_id=UUID(r.chunk_id),
                content=r.chunk_text,
                similarity_score=r.similarity_score,
                confidence=r.confidence,
                reason=r.reason,
            )
            for r in results
        ],
    )
    return APIResponse[MemorySearchResponse](success=True, data=response)


@router.get("/statistics", response_model=APIResponse[MemoryStatisticsResponse])
def get_statistics(manager: MemoryManagerDep, user: CurrentUser) -> APIResponse[MemoryStatisticsResponse]:
    stats = manager.get_statistics(user.id)
    return APIResponse[MemoryStatisticsResponse](success=True, data=MemoryStatisticsResponse(**stats))


@router.delete("/session", response_model=APIResponse[dict])
def end_session(
    manager: MemoryManagerDep, user: CurrentUser, session_id: str = Query(...)
) -> APIResponse[dict]:
    manager.end_session(session_id)
    return APIResponse[dict](success=True, data={"session_id": session_id, "ended": True})


@router.delete("/history", response_model=APIResponse[DeleteHistoryResponse])
def delete_history(
    manager: MemoryManagerDep,
    user: CurrentUser,
    memory_type: MemoryType | None = Query(default=None),
) -> APIResponse[DeleteHistoryResponse]:
    deleted_count = manager.delete_history(user.id, memory_type=memory_type)
    return APIResponse[DeleteHistoryResponse](
        success=True,
        data=DeleteHistoryResponse(deleted_count=deleted_count, memory_type=memory_type.value if memory_type else None),
    )


@router.delete("/prune", response_model=APIResponse[PruneResponse])
def prune_memory(
    manager: MemoryManagerDep,
    user: CurrentUser,
    keep_top_n_long_term: int = Query(default=1000, ge=0),
) -> APIResponse[PruneResponse]:
    result = manager.prune(user.id, keep_top_n_long_term=keep_top_n_long_term)
    return APIResponse[PruneResponse](success=True, data=PruneResponse(**result))


@router.post("/clear", response_model=APIResponse[ClearMemoryResponse])
def clear_memory(manager: MemoryManagerDep, user: CurrentUser) -> APIResponse[ClearMemoryResponse]:
    cleared_count = manager.clear_all(user.id)
    return APIResponse[ClearMemoryResponse](success=True, data=ClearMemoryResponse(cleared_count=cleared_count))
