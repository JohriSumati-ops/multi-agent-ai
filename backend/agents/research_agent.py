"""
agents/research_agent.py — Phase 6

WHY THIS FILE EXISTS
---------------------
The general-purpose entry point for an open research question — runs the
full pipeline (docs/Phase6.md Section 12) via `ResearchReasoningService`,
built by `reasoning/factory.py`. Thin by design, per this project's
established "agent wraps one reasoning-layer component" shape (Phase 2's
PDFParsingAgent set this precedent).

INPUT (via context.intermediate_results): "db" (Session), "user_id" (UUID),
"query" (str), "document_id" (UUID | None, optional).
OUTPUT: `ResearchResult` (reasoning/research_reasoning_service.py).
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError
from llm.prompts.templates import RESEARCH_QUERY_TEMPLATE
from reasoning.factory import build_research_reasoning_service
from reasoning.research_reasoning_service import ResearchResult


class ResearchAgent(BaseAgent):
    name = "research_agent"

    def validate_input(self, context: TaskContext) -> None:
        for key in ("db", "user_id", "query"):
            if key not in context.intermediate_results:
                raise ValidationAppError(f"ResearchAgent requires '{key}' in intermediate_results")

    def execute(self, context: TaskContext) -> ResearchResult:
        db = context.intermediate_results["db"]
        user_id = context.intermediate_results["user_id"]
        query = context.intermediate_results["query"]
        document_id = context.intermediate_results.get("document_id")
        llm_backend = context.intermediate_results.get("llm_backend")  # test-only override

        service = build_research_reasoning_service(db, user_id=user_id, llm_backend=llm_backend)
        result = service.run(
            user_id=user_id,
            query=query,
            template=RESEARCH_QUERY_TEMPLATE,
            document_id=document_id,
            include_synthesis=True,
            similarity_threshold=context.intermediate_results.get("similarity_threshold"),
        )
        context.intermediate_results["research_result"] = result
        return result

    def validate_output(self, output: ResearchResult) -> None:
        if output.used_llm and output.answer is None:
            raise ValidationAppError("ResearchAgent reported used_llm=True but produced no answer")
