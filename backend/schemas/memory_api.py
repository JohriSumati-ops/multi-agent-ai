"""
schemas/memory_api.py — Phase 4

Request/response contracts for the memory API. Kept separate from
`schemas/memory.py` (Phase 1, untouched) per docs/Phase4.md Section 9 —
that file's `MemoryCreate`/`MemoryOut` are the general-purpose ORM-facing
schemas; this file is specifically what the new REST endpoints accept and
return, including fields (session_id, search scores, statistics) that
don't belong on a generic Memory representation.

Every ID field here is typed `UUID`, not `str` — see docs/Phase4.md
Section 11's explicit callout of Phase 2's `owner_id: str` bug as a known
trap for every new schema this project adds.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from core.config import settings
from models.memory import MemoryType


class MemoryStoreRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)
    persist_long_term: bool = Field(
        default=False, description="False = short-term (expires); True = long-term (semantically indexed)."
    )
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    conversation_id: UUID | None = None
    document_id: UUID | None = None


class MemoryRecordOut(BaseModel):
    id: UUID
    user_id: UUID
    memory_type: MemoryType
    content: str
    importance_score: float
    expires_at: datetime | None
    conversation_id: UUID | None
    document_id: UUID | None
    created_at: datetime


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=settings.RETRIEVAL_TOP_K_DEFAULT, ge=1, le=50)
    similarity_threshold: float = Field(default=settings.RETRIEVAL_SIMILARITY_THRESHOLD, ge=-1.0, le=1.0)


class MemorySearchResultOut(BaseModel):
    rank: int
    memory_id: UUID
    content: str
    similarity_score: float
    confidence: float
    reason: str


class MemorySearchResponse(BaseModel):
    query: str
    result_count: int
    results: list[MemorySearchResultOut]


class SessionStateResponse(BaseModel):
    session_id: str
    state: dict


class MemoryStatisticsResponse(BaseModel):
    total_memories: int
    counts_by_type: dict[str, int]
    total_accesses: int
    expired_pending_cleanup: int
    most_accessed_memory_ids: list[str]
    memory_health: str


class PruneResponse(BaseModel):
    expired_deleted: int
    over_cap_pruned: int
    archived: int


class DeleteHistoryResponse(BaseModel):
    deleted_count: int
    memory_type: str | None


class ClearMemoryResponse(BaseModel):
    cleared_count: int
