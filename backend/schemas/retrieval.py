"""
schemas/retrieval.py — Phase 3

Request/response contracts for the retrieval API. `RankedResultOut`
mirrors `retrieval/ranking.py::RankedResult` field-for-field — kept as a
separate Pydantic schema (rather than serializing the dataclass directly)
for the same reason Phase 1 established schemas as distinct from ORM
models: the API's contract with clients should change deliberately, not as
a side effect of an internal dataclass's field names changing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.config import settings


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=settings.RETRIEVAL_TOP_K_DEFAULT, ge=1, le=50)
    similarity_threshold: float = Field(default=settings.RETRIEVAL_SIMILARITY_THRESHOLD, ge=-1.0, le=1.0)
    document_id: str | None = Field(default=None, description="Optional: restrict search to one document.")


class SimilarChunkRequest(BaseModel):
    chunk_id: str
    top_k: int = Field(default=settings.RETRIEVAL_TOP_K_DEFAULT, ge=1, le=50)
    similarity_threshold: float = Field(default=settings.RETRIEVAL_SIMILARITY_THRESHOLD, ge=-1.0, le=1.0)


class RankedResultOut(BaseModel):
    rank: int
    chunk_id: str
    document_id: str
    document_title: str
    chunk_text: str
    page_number: int | None
    chunk_index: int
    similarity_score: float
    confidence: float
    reason: str


class SearchResponse(BaseModel):
    query: str
    result_count: int
    results: list[RankedResultOut]


class DocumentRetrievalStatus(BaseModel):
    document_id: str
    title: str
    status: str
    chunk_count: int
    embedded_chunk_count: int
    is_fully_embedded: bool


class ChunkVectorInfo(BaseModel):
    chunk_id: str
    document_id: str
    vector_id: int
    embedding_model: str
    dimension: int


class ReindexResponse(BaseModel):
    document_id: str
    chunks_embedded: int
    status: str


class RebuildResponse(BaseModel):
    documents_processed: int
    chunks_embedded: int
    vectors_in_index: int
