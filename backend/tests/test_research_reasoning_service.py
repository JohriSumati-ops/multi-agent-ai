"""
tests/test_research_reasoning_service.py
"""

from __future__ import annotations

import json

from core.exceptions import GroundingViolationError, LLMResponseError
from llm.base_llm import LLMResponse
from llm.llm_service import LLMService
from llm.prompts.builder import PromptBuilder
from llm.prompts.templates import RESEARCH_QUERY_TEMPLATE
from models.user import User
from reasoning.citation_injector import CitationInjector
from reasoning.context_assembler import ContextAssembler
from reasoning.research_reasoning_service import ResearchReasoningService
from reasoning.response_validator import ResponseValidator
from reasoning.source_grounding import SourceGrounding
from repositories.document_chunk_repository import DocumentChunkRepository
from repositories.document_repository import DocumentRepository
from repositories.memory_repository import MemoryRepository
from services.long_term_memory_service import LongTermMemoryService
from services.memory_manager import MemoryManager
from services.semantic_search_service import SemanticSearchService
from tests.fakes import FakeLLMBackend


def _make_user(db_session, email="pipeline@example.com") -> User:
    user = User(email=email, hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_service(db_session, backend: FakeLLMBackend) -> ResearchReasoningService:
    return ResearchReasoningService(
        context_assembler=ContextAssembler(search_service=SemanticSearchService(db_session), memory_manager=MemoryManager(db_session)),
        prompt_builder=PromptBuilder(),
        llm_service=LLMService(backend),
        response_validator=ResponseValidator(),
        source_grounding=SourceGrounding(),
        citation_injector=CitationInjector(
            document_chunks=DocumentChunkRepository(db_session),
            documents=DocumentRepository(db_session),
            memories=MemoryRepository(db_session),
        ),
    )


def test_pipeline_skips_llm_when_no_context_exists(db_session) -> None:
    user = _make_user(db_session)
    backend = FakeLLMBackend()
    service = _make_service(db_session, backend)

    result = service.run(user_id=user.id, query="anything with no data", template=RESEARCH_QUERY_TEMPLATE)
    assert result.used_llm is False
    assert result.fallback_reason is not None
    assert backend.call_count == 0


def test_pipeline_produces_grounded_answer(db_session) -> None:
    user = _make_user(db_session)
    memory = LongTermMemoryService(db_session).write(user.id, "Binary trees support O(log n) lookup.")

    backend = FakeLLMBackend()
    backend.queued_responses = [
        LLMResponse(
            content=json.dumps(
                {
                    "answer": "Binary trees support O(log n) lookup.",
                    "sources_used": [{"chunk_id": str(memory.id), "document_title": "memory", "relevance": "high"}],
                    "confidence": 0.9,
                    "reasoning_summary": "Derived from remembered context.",
                    "memory_references": [str(memory.id)],
                }
            ),
            model_name="fake",
            input_tokens=30,
            output_tokens=10,
        )
    ]
    service = _make_service(db_session, backend)
    result = service.run(user_id=user.id, query="How fast is binary tree lookup?", template=RESEARCH_QUERY_TEMPLATE, similarity_threshold=-1.0)

    assert result.used_llm is True
    assert result.answer.answer == "Binary trees support O(log n) lookup."
    assert result.grounding_report.is_grounded is True
    assert len(result.citations) == 1
    assert result.prompt_tokens == 30
    assert result.completion_tokens == 10


def test_pipeline_raises_grounding_violation_for_fabricated_citation(db_session) -> None:
    user = _make_user(db_session)
    LongTermMemoryService(db_session).write(user.id, "Binary trees support O(log n) lookup.")

    backend = FakeLLMBackend()
    backend.queued_responses = [
        LLMResponse(
            content=json.dumps(
                {
                    "answer": "Fabricated answer.",
                    "sources_used": [{"chunk_id": "totally-fabricated-id", "document_title": "?", "relevance": "?"}],
                    "confidence": 0.9,
                    "reasoning_summary": "?",
                    "memory_references": [],
                }
            ),
            model_name="fake",
        )
    ]
    service = _make_service(db_session, backend)
    try:
        service.run(user_id=user.id, query="binary tree lookup speed", template=RESEARCH_QUERY_TEMPLATE, similarity_threshold=-1.0)
        assert False, "expected GroundingViolationError"
    except GroundingViolationError:
        pass


def test_pipeline_raises_for_malformed_llm_output(db_session) -> None:
    user = _make_user(db_session)
    LongTermMemoryService(db_session).write(user.id, "Some remembered fact.")

    backend = FakeLLMBackend()
    backend.queued_responses = [LLMResponse(content="not valid json at all", model_name="fake")]
    service = _make_service(db_session, backend)

    try:
        service.run(user_id=user.id, query="some remembered fact", template=RESEARCH_QUERY_TEMPLATE, similarity_threshold=-1.0)
        assert False, "expected LLMResponseError"
    except LLMResponseError:
        pass


def test_pipeline_includes_synthesis_when_requested(db_session) -> None:
    user = _make_user(db_session)
    memory = LongTermMemoryService(db_session).write(user.id, "Binary trees support O(log n) lookup.")

    backend = FakeLLMBackend()
    backend.queued_responses = [
        LLMResponse(
            content=json.dumps(
                {
                    "answer": "A",
                    "sources_used": [{"chunk_id": str(memory.id)}],
                    "confidence": 0.8,
                    "reasoning_summary": "S",
                    "memory_references": [],
                }
            ),
            model_name="fake",
        )
    ]
    service = _make_service(db_session, backend)
    result = service.run(user_id=user.id, query="binary tree lookup", template=RESEARCH_QUERY_TEMPLATE, include_synthesis=True, similarity_threshold=-1.0)
    assert result.synthesis is not None
    assert result.synthesis.evidence_count == 1
