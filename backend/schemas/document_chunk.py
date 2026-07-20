"""
schemas/document_chunk.py — Phase 2
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from models.document_chunk import ChunkingStrategy
from schemas.base import TimestampedSchema


class DocumentChunkOut(TimestampedSchema):
    document_id: UUID
    chunk_index: int
    chunk_text: str
    page_number: int | None = None
    start_position: int
    end_position: int
    token_count: int
    char_count: int
    chunking_strategy: ChunkingStrategy


class ChunkingRequest(BaseModel):
    """
    Optional request body for re-chunking a document with a specific
    strategy/parameters — used by `POST /documents/{id}/chunks` if exposed
    later; the initial upload pipeline uses sensible defaults (see
    `services/document_service.py::DEFAULT_CHUNKING_STRATEGY`).
    """

    strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH
    chunk_size: int | None = None
    overlap: int | None = None
