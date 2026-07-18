"""
schemas/document.py

Request/response contracts for the Document resource. Phase 1 has no upload
endpoint yet (that arrives with the PDF Parsing Agent in Phase 1's
successor), but the schema is defined now so the model, repository, and
schema are all in place together.
"""

from __future__ import annotations

from pydantic import BaseModel

from models.document import DocumentStatus, DocumentType
from schemas.base import TimestampedSchema


class DocumentCreate(BaseModel):
    title: str
    file_name: str
    file_path: str
    file_size_bytes: int | None = None
    document_type: DocumentType = DocumentType.OTHER
    subject: str | None = None
    description: str | None = None


class DocumentOut(TimestampedSchema):
    owner_id: str
    title: str
    file_name: str
    document_type: DocumentType
    status: DocumentStatus
    subject: str | None = None
    description: str | None = None
    processing_error: str | None = None
