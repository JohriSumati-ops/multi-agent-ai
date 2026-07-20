"""
document_processing/pipeline.py — THE PROCESSING PIPELINE

WHY THIS FILE EXISTS
---------------------
Phase 2's ingestion pipeline (Upload -> Validation -> Storage -> PDF
Parsing -> Metadata -> Cleaning -> Chunking -> Database) has one step that
needs a single, obvious home to be sequenced correctly: this file. It is
deliberately pure with respect to the database — it accepts a file path
and returns a fully-computed result object; `services/document_service.py`
is the only code that actually writes anything to Postgres, per the
Repository Pattern boundary established in Phase 1.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Separating "compute the pipeline's result" (this file — pure, easily unit
tested with a temp file and no database) from "persist the pipeline's
result" (`DocumentService` — impure, requires a `Session`) is the same
principle behind keeping repositories and services separate: the more of
your logic that doesn't need a live database to test, the faster and more
reliable your test suite is.

HOW THIS PREPARES FOR PHASE 3
---------------------------------
`ProcessingResult.chunks` is exactly Phase 3's Embedding Agent's input.
Nothing about this pipeline changes when Phase 3 adds an embedding step
after it — it's a new stage appended to the sequence, not a rewrite of
this one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agents.metadata_extraction_agent import ExtractedMetadata, MetadataExtractionAgent
from agents.pdf_parsing_agent import PDFParsingAgent
from core.agent_bus import TaskContext
from core.logging import get_logger
from document_processing.text_cleaner import clean_text
from models.document import DocumentFormat
from retrieval.chunker import Chunk, ChunkStrategyName, chunk_text
from schemas.agent_response import AgentResult

logger = get_logger("agent")

DEFAULT_CHUNK_STRATEGY = ChunkStrategyName.PARAGRAPH
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200


@dataclass
class ProcessingResult:
    cleaned_text: str
    metadata: ExtractedMetadata
    chunks: list[Chunk]
    agent_results: list[AgentResult] = field(default_factory=list)


def process_document(
    *,
    file_path: str,
    file_format: DocumentFormat,
    original_filename: str,
    user_id: str,
    document_id: str,
    chunk_strategy: ChunkStrategyName = DEFAULT_CHUNK_STRATEGY,
) -> ProcessingResult:
    """
    Runs the full Phase 2 pipeline (parse -> extract metadata -> clean ->
    chunk) for one document and returns the computed result, WITHOUT
    writing anything to the database.

    Raises whatever `core.exceptions.AppException` subclass the failing
    step raises (`CorruptedDocumentError`, `EmptyDocumentError`,
    `EncryptedDocumentError`, `UnsupportedFileTypeError`) — the caller
    (`DocumentService`) is responsible for catching these and marking the
    `Document` row FAILED with the error message.
    """
    context = TaskContext(
        user_id=user_id,
        original_query="",
        active_document_ids=[document_id],
    )
    context.intermediate_results["file_path"] = file_path
    context.intermediate_results["file_format"] = file_format
    context.intermediate_results["original_filename"] = original_filename

    agent_results: list[AgentResult] = []

    # --- Stage: PDF Parsing (agent #1) ---
    parse_result = PDFParsingAgent().run(context)
    agent_results.append(parse_result)
    if not parse_result.success:
        # `run()` never raises — it captures failures into AgentResult.
        # The pipeline re-raises here so DocumentService's error handling
        # (which maps exception types to processing_error text and HTTP
        # status) stays centralized in core/exceptions.py rather than
        # duplicated as string-matching on AgentResult.error_message.
        raise _reraise_original_failure(parse_result)

    # --- Stage: Metadata Extraction (agent #2) ---
    metadata_result = MetadataExtractionAgent().run(context)
    agent_results.append(metadata_result)
    if not metadata_result.success:
        raise _reraise_original_failure(metadata_result)

    metadata: ExtractedMetadata = metadata_result.output
    parsed = context.intermediate_results["parsed_document"]

    # --- Stage: Cleaning (not an agent — deterministic text transform) ---
    pages_text = [p.text for p in parsed.pages] if parsed.pages else None
    cleaned = clean_text(parsed.raw_text, pages_text=pages_text)

    # --- Stage: Chunking (not an agent — deterministic text transform) ---
    chunk_kwargs: dict = {}
    if chunk_strategy in (ChunkStrategyName.FIXED_SIZE, ChunkStrategyName.SLIDING_WINDOW):
        chunk_kwargs["chunk_size"] = DEFAULT_CHUNK_SIZE
        if chunk_strategy == ChunkStrategyName.SLIDING_WINDOW:
            chunk_kwargs["overlap"] = DEFAULT_OVERLAP
    else:
        chunk_kwargs["max_chunk_size"] = DEFAULT_CHUNK_SIZE

    chunks = chunk_text(cleaned, strategy=chunk_strategy, **chunk_kwargs)

    logger.info(
        "Pipeline complete for document_id=%s: %d chunks (%s strategy)",
        document_id,
        len(chunks),
        chunk_strategy,
    )

    return ProcessingResult(
        cleaned_text=cleaned,
        metadata=metadata,
        chunks=chunks,
        agent_results=agent_results,
    )


def _reraise_original_failure(result: AgentResult) -> Exception:
    """
    `BaseAgent.run()` swallows exceptions into `AgentResult` (by design —
    see agents/base_agent.py's docstring) but preserves the original
    exception's `error_code`/`error_status_code` when it was one of our
    own `AppException` subclasses. This reconstructs a typed exception
    from that preserved information so `DocumentService` (and the global
    exception handler) still report the correct HTTP status — e.g., 422
    for a corrupted PDF, not a generic 500 — even though the original
    exception *instance* wasn't preserved, only its shape.
    """
    from core.exceptions import AppException

    class ReraisedAgentError(AppException):
        pass

    error = ReraisedAgentError(
        result.error_message or f"{result.agent_name} failed with no error message"
    )
    error.status_code = result.error_status_code or 500
    error.error_code = result.error_code or "agent_execution_error"
    return error
