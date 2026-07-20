"""
schemas/document.py

Request/response contracts for the Document resource.

PHASE 2 UPDATE: `DocumentOut` now exposes the metadata fields the Metadata
Extraction Agent populates (`author`, `page_count`, `language`,
`word_count`, `char_count`, `reading_time_minutes`, `file_format`).
`DocumentCreate` is used internally by the upload service, not accepted
directly from the client — the client sends a multipart file upload (see
`api/routes/documents.py`), not a JSON body with a `file_path` a client
could forge.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from models.document import DocumentFormat, DocumentStatus, DocumentType
from schemas.base import TimestampedSchema


class DocumentCreate(BaseModel):
    title: str
    file_name: str
    file_path: str
    file_size_bytes: int | None = None
    file_format: DocumentFormat | None = None
    document_type: DocumentType = DocumentType.OTHER
    subject: str | None = None
    description: str | None = None


class DocumentOut(TimestampedSchema):
    owner_id: UUID
    title: str
    file_name: str
    file_format: DocumentFormat | None = None
    document_type: DocumentType
    status: DocumentStatus
    subject: str | None = None
    description: str | None = None
    processing_error: str | None = None

    # --- Phase 2 metadata ---
    author: str | None = None
    page_count: int | None = None
    language: str | None = None
    word_count: int | None = None
    char_count: int | None = None
    reading_time_minutes: float | None = None
