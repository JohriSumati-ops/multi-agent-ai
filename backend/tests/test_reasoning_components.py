"""
tests/test_reasoning_components.py

Covers ResponseValidator, SourceGrounding, CitationInjector, and
research_synthesis.py — all pure/DB-backed components with no LLM
involvement.
"""

from __future__ import annotations

import json

from core.exceptions import GroundingViolationError, LLMResponseError
from models.document import Document, DocumentFormat, DocumentStatus, DocumentType
from models.document_chunk import ChunkingStrategy, DocumentChunk
from models.user import User
from reasoning.citation_injector import CitationInjector
from reasoning.context_assembler import AssembledContext, ContextItem
from reasoning.research_synthesis import detect_conflicts, synthesize
from reasoning.response_validator import ResponseValidator
from reasoning.source_grounding import SourceGrounding
from repositories.document_chunk_repository import DocumentChunkRepository
from repositories.document_repository import DocumentRepository
from repositories.memory_repository import MemoryRepository

VALID_JSON = json.dumps(
    {
        "answer": "Trees are hierarchical structures.",
        "sources_used": [{"chunk_id": "c1", "document_title": "Notes", "relevance": "high"}],
        "confidence": 0.85,
        "reasoning_summary": "Based on source 1.",
        "memory_references": [],
    }
)


# ------------------------------------------------------------------ #
# ResponseValidator
# ------------------------------------------------------------------ #
def test_validate_accepts_well_formed_json() -> None:
    answer = ResponseValidator().validate(VALID_JSON)
    assert answer.answer == "Trees are hierarchical structures."
    assert answer.confidence == 0.85


def test_validate_strips_markdown_code_fence() -> None:
    fenced = f"```json\n{VALID_JSON}\n```"
    answer = ResponseValidator().validate(fenced)
    assert answer.answer == "Trees are hierarchical structures."


def test_validate_rejects_non_json_text() -> None:
    try:
        ResponseValidator().validate("This is just prose, not JSON.")
        assert False, "expected LLMResponseError"
    except LLMResponseError as e:
        assert "raw_response" in e.details


def test_validate_rejects_json_missing_required_fields() -> None:
    incomplete = json.dumps({"answer": "x"})
    try:
        ResponseValidator().validate(incomplete)
        assert False, "expected LLMResponseError"
    except LLMResponseError:
        pass


def test_validate_rejects_confidence_out_of_bounds() -> None:
    bad = json.dumps(
        {"answer": "x", "sources_used": [], "confidence": 1.5, "reasoning_summary": "y", "memory_references": []}
    )
    try:
        ResponseValidator().validate(bad)
        assert False, "expected LLMResponseError"
    except LLMResponseError:
        pass


# ------------------------------------------------------------------ #
# SourceGrounding
# ------------------------------------------------------------------ #
def test_grounding_passes_when_all_citations_are_real() -> None:
    context = AssembledContext(query="q")
    context.items.append(ContextItem(source_type="document_chunk", source_id="c1", title="Notes", text="...", relevance_score=0.9))
    answer = ResponseValidator().validate(VALID_JSON)

    report = SourceGrounding().verify(answer, context)
    assert report.is_grounded is True
    assert report.fabricated_chunk_ids == []


def test_grounding_raises_for_fabricated_citation_strict() -> None:
    context = AssembledContext(query="q")  # no items provided at all
    answer = ResponseValidator().validate(VALID_JSON)  # cites "c1", which was never provided

    try:
        SourceGrounding().verify(answer, context, strict=True)
        assert False, "expected GroundingViolationError"
    except GroundingViolationError as e:
        assert "c1" in str(e.details["fabricated_chunk_ids"])


def test_grounding_non_strict_returns_report_instead_of_raising() -> None:
    context = AssembledContext(query="q")
    answer = ResponseValidator().validate(VALID_JSON)

    report = SourceGrounding().verify(answer, context, strict=False)
    assert report.is_grounded is False
    assert "c1" in report.fabricated_chunk_ids


# ------------------------------------------------------------------ #
# CitationInjector
# ------------------------------------------------------------------ #
def _make_user_document_chunk(db_session):
    user = User(email="citation@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    document = Document(
        owner_id=user.id, title="Trees Notes", file_name="trees.txt", file_path="/tmp/trees.txt",
        file_format=DocumentFormat.TXT, document_type=DocumentType.OTHER, status=DocumentStatus.CHUNKED,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    chunk = DocumentChunk(
        document_id=document.id, chunk_index=2, chunk_text="A tree is hierarchical.",
        page_number=3, start_position=0, end_position=24, token_count=4, char_count=24,
        chunking_strategy=ChunkingStrategy.PARAGRAPH,
    )
    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)
    return user, document, chunk


def test_citation_injector_resolves_document_chunk(db_session) -> None:
    user, document, chunk = _make_user_document_chunk(db_session)
    injector = CitationInjector(
        document_chunks=DocumentChunkRepository(db_session),
        documents=DocumentRepository(db_session),
        memories=MemoryRepository(db_session),
    )
    citations = injector.inject([str(chunk.id)])
    assert len(citations) == 1
    assert "Trees Notes" in citations[0].citation_text
    assert "page 3" in citations[0].citation_text
    assert citations[0].is_memory is False


def test_citation_injector_resolves_memory(db_session) -> None:
    from services.long_term_memory_service import LongTermMemoryService

    user = User(email="citmem@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    memory = LongTermMemoryService(db_session).write(user.id, "A remembered fact.")
    injector = CitationInjector(
        document_chunks=DocumentChunkRepository(db_session),
        documents=DocumentRepository(db_session),
        memories=MemoryRepository(db_session),
    )
    citations = injector.inject([str(memory.id)])
    assert len(citations) == 1
    assert citations[0].is_memory is True


def test_citation_injector_skips_invalid_ids(db_session) -> None:
    injector = CitationInjector(
        document_chunks=DocumentChunkRepository(db_session),
        documents=DocumentRepository(db_session),
        memories=MemoryRepository(db_session),
    )
    citations = injector.inject(["not-a-uuid", "00000000-0000-0000-0000-000000000000"])
    assert citations == []


# ------------------------------------------------------------------ #
# research_synthesis
# ------------------------------------------------------------------ #
def test_detect_conflicts_flags_negation_disagreement() -> None:
    items = [
        ContextItem(source_type="document_chunk", source_id="a", title="A", text="Coffee improves alertness significantly.", relevance_score=0.9),
        ContextItem(source_type="document_chunk", source_id="b", title="B", text="Coffee does not improve alertness in most studies.", relevance_score=0.85),
    ]
    conflicts = detect_conflicts(items)
    assert len(conflicts) == 1


def test_detect_conflicts_ignores_unrelated_sources() -> None:
    items = [
        ContextItem(source_type="document_chunk", source_id="a", title="A", text="Coffee improves alertness.", relevance_score=0.9),
        ContextItem(source_type="document_chunk", source_id="b", title="B", text="Tea has antioxidants.", relevance_score=0.5),
    ]
    conflicts = detect_conflicts(items)
    assert conflicts == []


def test_synthesize_empty_evidence() -> None:
    result = synthesize([])
    assert result.evidence_count == 0
    assert "No evidence" in result.consensus_note


def test_synthesize_reports_average_relevance() -> None:
    items = [
        ContextItem(source_type="document_chunk", source_id="a", title="A", text="text one here", relevance_score=0.8),
        ContextItem(source_type="document_chunk", source_id="b", title="B", text="text two here", relevance_score=0.6),
    ]
    result = synthesize(items)
    assert result.average_relevance == 0.7
