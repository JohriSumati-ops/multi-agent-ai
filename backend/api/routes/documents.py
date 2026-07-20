"""
api/routes/documents.py — Phase 2

WHY THIS FILE EXISTS
---------------------
The HTTP surface for the entire Document Intelligence Pipeline. Per the
Phase 1 "routers are transport-only" rule, every handler here does nothing
but: read the request, call `DocumentService`, and shape the response —
all validation, storage, parsing, and chunking logic lives in
`DocumentService` and the modules it calls.

ENDPOINTS (per the Phase 2 spec)
--------------------------------------
- `POST /documents/upload` — multipart file upload, runs the full pipeline
  synchronously and returns the processed document (or a 4xx with a
  specific reason if any pipeline stage fails).
- `GET /documents` — list the current user's documents.
- `GET /documents/{id}` — fetch one document's metadata.
- `DELETE /documents/{id}` — remove a document and its chunks + file.
- `GET /documents/{id}/chunks` — fetch a document's chunks.

All routes require authentication (`CurrentUser`) and enforce ownership —
a user can never read or delete another user's document, even by guessing
a UUID.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, UploadFile

from api.deps import CurrentUser, DocumentServiceDep
from core.exceptions import NotFoundError
from models.document import Document
from schemas.base import APIResponse
from schemas.document import DocumentOut
from schemas.document_chunk import DocumentChunkOut

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_owned_document_or_404(service: DocumentServiceDep, document_id: UUID, user: CurrentUser) -> Document:
    document = service.get_document(document_id)
    if document is None or document.owner_id != user.id:
        # Deliberately the same 404 whether the document doesn't exist or
        # belongs to someone else — a 403 would confirm to an attacker
        # that a given UUID exists but isn't theirs.
        raise NotFoundError("Document not found")
    return document


@router.post("/upload", response_model=APIResponse[DocumentOut], status_code=201)
async def upload_document(
    service: DocumentServiceDep,
    user: CurrentUser,
    file: UploadFile = File(...),
) -> APIResponse[DocumentOut]:
    content = await file.read()
    document = service.upload_and_process(
        owner_id=user.id,
        content=content,
        original_filename=file.filename or "unnamed",
    )
    return APIResponse[DocumentOut](success=True, data=DocumentOut.model_validate(document))


@router.get("", response_model=APIResponse[list[DocumentOut]])
def list_documents(service: DocumentServiceDep, user: CurrentUser) -> APIResponse[list[DocumentOut]]:
    documents = service.list_for_owner(user.id)
    return APIResponse[list[DocumentOut]](
        success=True, data=[DocumentOut.model_validate(d) for d in documents]
    )


@router.get("/{document_id}", response_model=APIResponse[DocumentOut])
def get_document(document_id: UUID, service: DocumentServiceDep, user: CurrentUser) -> APIResponse[DocumentOut]:
    document = _get_owned_document_or_404(service, document_id, user)
    return APIResponse[DocumentOut](success=True, data=DocumentOut.model_validate(document))


@router.delete("/{document_id}", response_model=APIResponse[dict], status_code=200)
def delete_document(document_id: UUID, service: DocumentServiceDep, user: CurrentUser) -> APIResponse[dict]:
    document = _get_owned_document_or_404(service, document_id, user)
    service.delete_document(document)
    return APIResponse[dict](success=True, data={"deleted": True, "document_id": str(document_id)})


@router.get("/{document_id}/chunks", response_model=APIResponse[list[DocumentChunkOut]])
def get_document_chunks(
    document_id: UUID, service: DocumentServiceDep, user: CurrentUser
) -> APIResponse[list[DocumentChunkOut]]:
    _get_owned_document_or_404(service, document_id, user)
    chunks = service.get_chunks(document_id)
    return APIResponse[list[DocumentChunkOut]](
        success=True, data=[DocumentChunkOut.model_validate(c) for c in chunks]
    )
