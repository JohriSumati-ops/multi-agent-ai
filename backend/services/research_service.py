"""
services/research_service.py — Phase 6

WHY THIS FILE EXISTS
---------------------
`api/routes/research.py` needs a service to depend on, following the exact
pattern every previous phase's API layer used
(`DocumentService`, `SemanticSearchService`, `MemoryManager`,
`OrchestrationService`). This class is thin: it builds a
`ResearchReasoningService` via `reasoning/factory.py`, runs it, and
persists the result as a `ResearchResponse` row for `/research/explain`
to later reconstruct — no reasoning logic of its own.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from core.exceptions import NotFoundError
from llm.prompts.templates import QUESTION_ANSWERING_TEMPLATE, RESEARCH_QUERY_TEMPLATE, SUMMARIZATION_TEMPLATE
from models.research_response import ResearchResponse
from reasoning.factory import build_context_assembler, build_research_reasoning_service
from reasoning.research_reasoning_service import ResearchResult
from reasoning.research_synthesis import SynthesisResult, synthesize
from repositories.research_response_repository import ResearchResponseRepository


class ResearchService:
    def __init__(self, db: Session, *, llm_backend=None) -> None:
        self.db = db
        self.llm_backend = llm_backend
        self.repo = ResearchResponseRepository(db)

    def _persist(self, user_id: UUID, result: ResearchResult) -> ResearchResponse | None:
        if not result.used_llm or result.answer is None:
            return None

        response = ResearchResponse(
            user_id=user_id,
            query_text=result.query,
            answer_text=result.answer.answer,
            confidence=result.answer.confidence,
            reasoning_summary=result.answer.reasoning_summary,
            sources_used=[s.model_dump() for s in result.answer.sources_used],
            memory_references=result.answer.memory_references,
            retrieved_chunk_ids=result.context.chunk_ids() if result.context else [],
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=result.latency_ms,
            explainability_payload={
                "citations": [c.__dict__ for c in result.citations],
                "grounding": result.grounding_report.__dict__ if result.grounding_report else None,
                "synthesis": result.synthesis.__dict__ if result.synthesis else None,
                "excluded_count": result.context.excluded_count if result.context else 0,
                "excluded_reasons": result.context.excluded_reasons if result.context else {},
            },
        )
        return self.repo.create(response)

    def query(self, *, user_id: UUID, query_text: str, document_id: UUID | None = None) -> tuple[ResearchResult, ResearchResponse | None]:
        service = build_research_reasoning_service(self.db, user_id=user_id, llm_backend=self.llm_backend)
        result = service.run(user_id=user_id, query=query_text, template=RESEARCH_QUERY_TEMPLATE, document_id=document_id)
        return result, self._persist(user_id, result)

    def answer(self, *, user_id: UUID, query_text: str, document_id: UUID | None = None) -> tuple[ResearchResult, ResearchResponse | None]:
        service = build_research_reasoning_service(self.db, user_id=user_id, llm_backend=self.llm_backend)
        result = service.run(
            user_id=user_id, query=query_text, template=QUESTION_ANSWERING_TEMPLATE,
            document_id=document_id, include_synthesis=False,
        )
        return result, self._persist(user_id, result)

    def summarize(self, *, user_id: UUID, query_text: str, document_id: UUID | None = None) -> tuple[ResearchResult, ResearchResponse | None]:
        service = build_research_reasoning_service(self.db, user_id=user_id, llm_backend=self.llm_backend)
        result = service.run(
            user_id=user_id, query=query_text, template=SUMMARIZATION_TEMPLATE,
            document_id=document_id, include_synthesis=False,
        )
        return result, self._persist(user_id, result)

    def reason(self, *, user_id: UUID, query_text: str, document_id: UUID | None = None) -> SynthesisResult:
        assembler = build_context_assembler(self.db)
        from core.config import settings

        context = assembler.assemble(
            user_id=user_id, query=query_text, token_budget=settings.LLM_CONTEXT_TOKEN_BUDGET, document_id=document_id
        )
        return synthesize(context.items)

    def explain(self, *, response_id: UUID, user_id: UUID) -> ResearchResponse:
        response = self.repo.get_owned(response_id, user_id)
        if response is None:
            raise NotFoundError("Research response not found")
        return response
