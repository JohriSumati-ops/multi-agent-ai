"""
services/document_service.py — Phase 2

WHY THIS FILE EXISTS
---------------------
The one place that combines "touching the filesystem," "touching the
database," and "running the processing pipeline" — none of which belong in
a router (transport-only), a repository (storage-only), or
`document_processing/pipeline.py` (deliberately pure/DB-free, see its
docstring). This is the Service Layer pattern from Phase 1, extended with
Phase 2's first genuinely multi-step orchestration.

PIPELINE STAGES IMPLEMENTED HERE
--------------------------------------
Upload -> Validation -> Storage -> [pipeline.process_document: PDF Parsing
-> Metadata -> Cleaning -> Chunking] -> Database persistence, exactly the
sequence from the Phase 2 spec. Validation and Storage happen here (not in
`pipeline.py`) because they're infrastructure concerns (disk I/O, request
validation), not document-understanding steps.

ERROR HANDLING
-----------------
Every failure mode the Phase 2 spec calls out — corrupted PDFs, oversized
files, unsupported formats, empty documents, encrypted PDFs — is handled
by letting the appropriate `core.exceptions.AppException` subclass
propagate. For failures that happen *after* the `Document` row already
exists (i.e., during `process_document`), the row is marked FAILED with
`processing_error` set, rather than being deleted — a failed upload should
remain visible to the user with an explanation, not silently vanish.
"""

from __future__ import annotations

import os
import uuid

from sqlalchemy.orm import Session

from core.agent_bus import TaskContext
from core.config import settings
from core.exceptions import AppException, FileTooLargeError, UnsupportedFileTypeError
from core.logging import get_logger
from document_processing.pipeline import DEFAULT_CHUNK_STRATEGY, process_document
from models.agent_execution_log import AgentExecutionLog, AgentExecutionStatus
from models.document import Document, DocumentFormat, DocumentStatus, DocumentType
from models.document_chunk import ChunkingStrategy, DocumentChunk
from repositories.agent_execution_log_repository import AgentExecutionLogRepository
from repositories.document_chunk_repository import DocumentChunkRepository
from repositories.document_repository import DocumentRepository
from retrieval.chunker import ChunkStrategyName

logger = get_logger("app")

_EXTENSION_TO_FORMAT = {
    "pdf": DocumentFormat.PDF,
    "txt": DocumentFormat.TXT,
    "md": DocumentFormat.MARKDOWN,
    "markdown": DocumentFormat.MARKDOWN,
    "docx": DocumentFormat.DOCX,
}

# Chunking strategy enums are intentionally duplicated across
# `retrieval.chunker.ChunkStrategyName` (in-memory chunking logic) and
# `models.document_chunk.ChunkingStrategy` (persisted column) — this map
# is the one place that reconciles them, so the pipeline and the ORM never
# need to import each other's enum.
_STRATEGY_TO_MODEL_ENUM = {
    ChunkStrategyName.FIXED_SIZE: ChunkingStrategy.FIXED_SIZE,
    ChunkStrategyName.PARAGRAPH: ChunkingStrategy.PARAGRAPH,
    ChunkStrategyName.SENTENCE: ChunkingStrategy.SENTENCE,
    ChunkStrategyName.SLIDING_WINDOW: ChunkingStrategy.SLIDING_WINDOW,
}


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.chunks = DocumentChunkRepository(db)
        self.agent_logs = AgentExecutionLogRepository(db)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    @staticmethod
    def validate_upload(filename: str, size_bytes: int) -> DocumentFormat:
        """
        Validates filename and size BEFORE any file content is trusted or
        written to disk. Returns the resolved `DocumentFormat` for
        convenience, since callers need it immediately afterward anyway.
        """
        if not filename or "." not in filename:
            raise UnsupportedFileTypeError("Uploaded file has no discernible extension.")

        extension = filename.rsplit(".", 1)[-1].lower()
        if extension not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"'.{extension}' is not a supported file type. "
                f"Supported types: {', '.join(settings.ALLOWED_DOCUMENT_EXTENSIONS)}"
            )

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise FileTooLargeError(
                f"File is {size_bytes / (1024 * 1024):.1f}MB, "
                f"which exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit."
            )
        if size_bytes == 0:
            from core.exceptions import EmptyDocumentError

            raise EmptyDocumentError("Uploaded file is empty (0 bytes).")

        return _EXTENSION_TO_FORMAT[extension]

    # ------------------------------------------------------------------ #
    # Storage
    # ------------------------------------------------------------------ #
    @staticmethod
    def store_file(content: bytes, original_filename: str) -> str:
        """
        Writes `content` to disk under a generated, collision-proof
        filename and returns the path written to.

        WHY a generated filename rather than the original: two users
        uploading "notes.pdf" on the same day must never collide on disk,
        and trusting a client-supplied filename directly is a path-
        traversal risk (`../../etc/passwd`) that a UUID-based name
        sidesteps entirely.
        """
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        extension = original_filename.rsplit(".", 1)[-1].lower()
        generated_name = f"{uuid.uuid4()}.{extension}"
        destination = os.path.join(settings.UPLOAD_DIR, generated_name)

        with open(destination, "wb") as f:
            f.write(content)

        return destination

    # ------------------------------------------------------------------ #
    # Upload + full pipeline
    # ------------------------------------------------------------------ #
    def upload_and_process(
        self,
        *,
        owner_id: uuid.UUID,
        content: bytes,
        original_filename: str,
        chunk_strategy: ChunkStrategyName = DEFAULT_CHUNK_STRATEGY,
    ) -> Document:
        """
        The full Phase 2 pipeline entry point: validate -> store -> create
        the Document row -> run the processing pipeline -> persist
        metadata + chunks -> mark CHUNKED (or FAILED with an explanation).
        """
        file_format = self.validate_upload(original_filename, len(content))
        file_path = self.store_file(content, original_filename)

        document = Document(
            owner_id=owner_id,
            title=original_filename,  # placeholder — overwritten by extracted metadata below
            file_name=original_filename,
            file_path=file_path,
            file_size_bytes=len(content),
            file_format=file_format,
            document_type=DocumentType.OTHER,
            status=DocumentStatus.UPLOADED,
        )
        document = self.documents.create(document)

        try:
            self._run_pipeline_and_persist(
                document=document,
                owner_id=owner_id,
                file_path=file_path,
                file_format=file_format,
                original_filename=original_filename,
                chunk_strategy=chunk_strategy,
            )
        except AppException as exc:
            document.status = DocumentStatus.FAILED
            document.processing_error = exc.message
            self.documents.commit_refresh(document)
            logger.warning("Document %s processing failed: %s", document.id, exc.message)
            raise

        return document

    def _run_pipeline_and_persist(
        self,
        *,
        document: Document,
        owner_id: uuid.UUID,
        file_path: str,
        file_format: DocumentFormat,
        original_filename: str,
        chunk_strategy: ChunkStrategyName,
    ) -> None:
        document.status = DocumentStatus.PARSING
        self.documents.commit_refresh(document)

        result = process_document(
            file_path=file_path,
            file_format=file_format,
            original_filename=original_filename,
            user_id=str(owner_id),
            document_id=str(document.id),
            chunk_strategy=chunk_strategy,
        )

        # --- Persist agent execution telemetry (Phase 1's logging table, used for real for the first time) ---
        task_id = str(uuid.uuid4())
        for step_order, agent_result in enumerate(result.agent_results):
            self.agent_logs.create(
                AgentExecutionLog(
                    task_id=task_id,
                    user_id=owner_id,
                    agent_name=agent_result.agent_name,
                    status=AgentExecutionStatus.SUCCESS
                    if agent_result.success
                    else AgentExecutionStatus.FAILED,
                    step_order=step_order,
                    latency_ms=agent_result.execution_time_ms,
                    error_message=agent_result.error_message,
                    extra_metadata={"document_id": str(document.id)},
                )
            )

        # --- Persist extracted metadata onto the Document row ---
        document.title = result.metadata.title
        document.author = result.metadata.author
        document.page_count = result.metadata.page_count
        document.language = result.metadata.language
        document.word_count = result.metadata.word_count
        document.char_count = result.metadata.char_count
        document.reading_time_minutes = result.metadata.reading_time_minutes
        document.status = DocumentStatus.PARSED
        self.documents.commit_refresh(document)

        # --- Persist chunks ---
        model_strategy = _STRATEGY_TO_MODEL_ENUM[chunk_strategy]
        chunk_rows = [
            DocumentChunk(
                document_id=document.id,
                chunk_index=c.chunk_index,
                chunk_text=c.text,
                page_number=c.page_number,
                start_position=c.start_position,
                end_position=c.end_position,
                token_count=c.token_count,
                char_count=c.char_count,
                chunking_strategy=model_strategy,
                extra_metadata=c.extra_metadata,
            )
            for c in result.chunks
        ]
        self.chunks.bulk_create(chunk_rows)

        document.status = DocumentStatus.CHUNKED
        document.processing_error = None
        self.documents.commit_refresh(document)

        logger.info(
            "Document %s fully processed: %d chunks, status=%s",
            document.id,
            len(chunk_rows),
            document.status,
        )

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    def get_document(self, document_id: uuid.UUID) -> Document | None:
        return self.documents.get(document_id)

    def list_for_owner(self, owner_id: uuid.UUID) -> list[Document]:
        return self.documents.list_for_owner(owner_id)

    def get_chunks(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        return self.chunks.list_for_document(document_id)

    def delete_document(self, document: Document) -> None:
        # Chunks cascade-delete via the ORM relationship's
        # cascade="all, delete-orphan" — no separate chunk cleanup needed.
        file_path = document.file_path
        self.documents.delete(document)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                logger.warning("Could not remove file from disk: %s", file_path)
