"""
reasoning/factory.py — RESEARCH REASONING SERVICE FACTORY

WHY THIS FILE EXISTS
---------------------
`orchestration/workflow_engine.py` instantiates every registered agent
with a no-argument constructor (`registration.agent_class()` — see
Phase 5's `_invoke_agent`). The five Phase 6 agents, unlike Phase 2/3's,
need a database session and several other dependencies to do anything
useful. Rather than have each of the five agents duplicate the same
seven-component wiring in its own `execute()` method, this one factory
function builds a fully-wired `ResearchReasoningService` (and its
component parts, for agents that only need one piece — e.g.,
`CitationAgent` only needs `CitationInjector`) from a `db` session pulled
out of `TaskContext.intermediate_results`, exactly the same
"db passed through intermediate_results" pattern
`services/orchestration_service.py` already established in Phase 5.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from llm.factory import get_llm_provider
from llm.llm_service import LLMService
from llm.prompts.builder import PromptBuilder
from reasoning.citation_injector import CitationInjector
from reasoning.context_assembler import ContextAssembler
from reasoning.research_reasoning_service import ResearchReasoningService
from reasoning.response_validator import ResponseValidator
from reasoning.source_grounding import SourceGrounding
from repositories.document_chunk_repository import DocumentChunkRepository
from repositories.document_repository import DocumentRepository
from repositories.llm_usage_log_repository import LLMUsageLogRepository
from repositories.memory_repository import MemoryRepository
from services.memory_manager import MemoryManager
from services.semantic_search_service import SemanticSearchService


def build_context_assembler(db: Session) -> ContextAssembler:
    return ContextAssembler(search_service=SemanticSearchService(db), memory_manager=MemoryManager(db))


def build_citation_injector(db: Session) -> CitationInjector:
    return CitationInjector(
        document_chunks=DocumentChunkRepository(db),
        documents=DocumentRepository(db),
        memories=MemoryRepository(db),
    )


def build_llm_service(db: Session, *, user_id: UUID | None = None, backend=None) -> LLMService:
    resolved_backend = backend or get_llm_provider()
    return LLMService(resolved_backend, usage_log_repo=LLMUsageLogRepository(db), user_id=user_id)


def build_research_reasoning_service(
    db: Session, *, user_id: UUID | None = None, llm_backend=None
) -> ResearchReasoningService:
    return ResearchReasoningService(
        context_assembler=build_context_assembler(db),
        prompt_builder=PromptBuilder(),
        llm_service=build_llm_service(db, user_id=user_id, backend=llm_backend),
        response_validator=ResponseValidator(),
        source_grounding=SourceGrounding(),
        citation_injector=build_citation_injector(db),
    )
