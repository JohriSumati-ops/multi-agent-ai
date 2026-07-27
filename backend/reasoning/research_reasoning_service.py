"""
reasoning/research_reasoning_service.py — THE REASONING PIPELINE ORCHESTRATOR

WHY THIS FILE EXISTS
---------------------
Composes every reasoning-layer component into the pipeline described in
docs/Phase6.md Section 12: assemble context -> (bail out if empty) ->
build prompt -> call the LLM -> validate -> verify grounding -> inject
citations -> return. Like every orchestrator in this project since
`services/orchestration_service.py` (Phase 5), this class contains no
reasoning logic of its own — every step is delegated to a component
that was built and tested independently.

WHY "INSUFFICIENT CONTEXT" IS A RETURNED RESULT, NOT AN EXCEPTION
--------------------------------------------------------------------------
`InsufficientContextError` exists in `core/exceptions.py`, but this
service does NOT raise it — it catches the empty-context case and returns
a `ResearchResult` with `used_llm=False` and an explanatory answer instead.
This is a deliberate API design choice: "I don't have enough information
to answer that" is a normal, expected outcome for a personal-document
research tool (the user hasn't uploaded anything relevant yet), not an
error condition — treating it as an HTTP error would make a completely
ordinary empty-library query look like a system failure to API clients.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from uuid import UUID

from core.config import settings
from core.logging import get_logger
from llm.llm_service import LLMService
from llm.prompts.builder import PromptBuilder
from llm.prompts.templates import PromptTemplate, StructuredAnswer
from reasoning.citation_injector import Citation, CitationInjector
from reasoning.context_assembler import AssembledContext, ContextAssembler
from reasoning.research_synthesis import SynthesisResult, synthesize
from reasoning.response_validator import ResponseValidator
from reasoning.source_grounding import GroundingReport, SourceGrounding

logger = get_logger("agent")


@dataclass
class ResearchResult:
    query: str
    used_llm: bool
    answer: StructuredAnswer | None = None
    citations: list[Citation] = field(default_factory=list)
    grounding_report: GroundingReport | None = None
    synthesis: SynthesisResult | None = None
    context: AssembledContext | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int = 0
    fallback_reason: str | None = None


class ResearchReasoningService:
    def __init__(
        self,
        *,
        context_assembler: ContextAssembler,
        prompt_builder: PromptBuilder,
        llm_service: LLMService,
        response_validator: ResponseValidator,
        source_grounding: SourceGrounding,
        citation_injector: CitationInjector,
    ) -> None:
        self.context_assembler = context_assembler
        self.prompt_builder = prompt_builder
        self.llm_service = llm_service
        self.response_validator = response_validator
        self.source_grounding = source_grounding
        self.citation_injector = citation_injector

    def run(
        self,
        *,
        user_id: UUID,
        query: str,
        template: PromptTemplate,
        document_id: UUID | None = None,
        include_synthesis: bool = True,
        similarity_threshold: float | None = None,
        task_id: str | None = None,
    ) -> ResearchResult:
        started = time.perf_counter()
        resolved_threshold = (
            similarity_threshold if similarity_threshold is not None else settings.RETRIEVAL_SIMILARITY_THRESHOLD
        )

        context = self.context_assembler.assemble(
            user_id=user_id,
            query=query,
            token_budget=settings.LLM_CONTEXT_TOKEN_BUDGET,
            document_id=document_id,
            similarity_threshold=resolved_threshold,
        )

        if context.is_empty:
            logger.info("No relevant context found for query — skipping LLM call (hallucination mitigation)")
            return ResearchResult(
                query=query,
                used_llm=False,
                context=context,
                fallback_reason=(
                    "No relevant documents or memory were found for this query. "
                    "Upload a relevant document or try rephrasing your question."
                ),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        messages = self.prompt_builder.build(template, context=context, query=query)
        llm_response = self.llm_service.generate(messages, task_id=task_id)

        answer = self.response_validator.validate(llm_response.content)
        grounding_report = self.source_grounding.verify(answer, context, strict=True)
        citations = self.citation_injector.inject([s.chunk_id for s in answer.sources_used])

        synthesis = synthesize(context.items) if include_synthesis else None

        return ResearchResult(
            query=query,
            used_llm=True,
            answer=answer,
            citations=citations,
            grounding_report=grounding_report,
            synthesis=synthesis,
            context=context,
            prompt_tokens=llm_response.input_tokens,
            completion_tokens=llm_response.output_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
