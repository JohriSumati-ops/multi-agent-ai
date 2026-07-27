"""
api/routes/research.py — Phase 6

WHY THIS FILE EXISTS
---------------------
The HTTP surface for the LLM Intelligence & Research Reasoning Layer. Per
the "routers are transport-only" rule established in Phase 1, and per this
phase's explicit "never call the LLM directly from routes" instruction,
every handler here does nothing but read the request, call
`ResearchService`, and shape the response.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from api.deps import CurrentUser, ResearchServiceDep
from schemas.base import APIResponse
from schemas.research import (
    CitationOut,
    ConflictOut,
    ExplainResponse,
    ReasoningResponse,
    ResearchAnswerOut,
    ResearchQueryRequest,
    SourceUsedOut,
)

router = APIRouter(prefix="/research", tags=["research"])


def _to_answer_out(result, response) -> ResearchAnswerOut:
    if not result.used_llm:
        return ResearchAnswerOut(used_llm=False, fallback_reason=result.fallback_reason, latency_ms=result.latency_ms)

    return ResearchAnswerOut(
        used_llm=True,
        answer=result.answer.answer,
        sources_used=[SourceUsedOut(**s.model_dump()) for s in result.answer.sources_used],
        citations=[CitationOut(**c.__dict__) for c in result.citations],
        confidence=result.answer.confidence,
        reasoning_summary=result.answer.reasoning_summary,
        memory_references=result.answer.memory_references,
        retrieved_chunk_ids=result.context.chunk_ids() if result.context else [],
        is_grounded=result.grounding_report.is_grounded if result.grounding_report else None,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=result.latency_ms,
        response_id=response.id if response else None,
    )


@router.post("/query", response_model=APIResponse[ResearchAnswerOut])
def research_query(
    payload: ResearchQueryRequest, service: ResearchServiceDep, user: CurrentUser
) -> APIResponse[ResearchAnswerOut]:
    result, response = service.query(user_id=user.id, query_text=payload.query, document_id=payload.document_id)
    return APIResponse[ResearchAnswerOut](success=True, data=_to_answer_out(result, response))


@router.post("/answer", response_model=APIResponse[ResearchAnswerOut])
def research_answer(
    payload: ResearchQueryRequest, service: ResearchServiceDep, user: CurrentUser
) -> APIResponse[ResearchAnswerOut]:
    result, response = service.answer(user_id=user.id, query_text=payload.query, document_id=payload.document_id)
    return APIResponse[ResearchAnswerOut](success=True, data=_to_answer_out(result, response))


@router.post("/summarize", response_model=APIResponse[ResearchAnswerOut])
def research_summarize(
    payload: ResearchQueryRequest, service: ResearchServiceDep, user: CurrentUser
) -> APIResponse[ResearchAnswerOut]:
    result, response = service.summarize(user_id=user.id, query_text=payload.query, document_id=payload.document_id)
    return APIResponse[ResearchAnswerOut](success=True, data=_to_answer_out(result, response))


@router.post("/reason", response_model=APIResponse[ReasoningResponse])
def research_reason(
    payload: ResearchQueryRequest, service: ResearchServiceDep, user: CurrentUser
) -> APIResponse[ReasoningResponse]:
    synthesis = service.reason(user_id=user.id, query_text=payload.query, document_id=payload.document_id)
    return APIResponse[ReasoningResponse](
        success=True,
        data=ReasoningResponse(
            evidence_count=synthesis.evidence_count,
            conflicts=[ConflictOut(**c.__dict__) for c in synthesis.conflicts],
            average_relevance=synthesis.average_relevance,
            consensus_note=synthesis.consensus_note,
        ),
    )


@router.get("/explain/{response_id}", response_model=APIResponse[ExplainResponse])
def research_explain(
    response_id: UUID, service: ResearchServiceDep, user: CurrentUser
) -> APIResponse[ExplainResponse]:
    response = service.explain(response_id=response_id, user_id=user.id)
    return APIResponse[ExplainResponse](
        success=True,
        data=ExplainResponse(
            response_id=response.id,
            query_text=response.query_text,
            answer_text=response.answer_text,
            confidence=response.confidence,
            reasoning_summary=response.reasoning_summary,
            sources_used=response.sources_used,
            memory_references=response.memory_references,
            retrieved_chunk_ids=response.retrieved_chunk_ids,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=response.latency_ms,
            explainability_payload=response.explainability_payload,
        ),
    )
