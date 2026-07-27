"""
agents/summarization_agent.py — Phase 6

WHY THIS FILE EXISTS
---------------------
Condenses retrieved/remembered context using `SUMMARIZATION_TEMPLATE`
(Section 14 of docs/Phase6.md) — "what does this material say," not "what
is the answer to X." `query` here is used purely as the retrieval query
(what context to gather), not as a question the model is instructed to
answer — the summarization template explicitly forbids answering an
implicit question.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError
from llm.prompts.templates import SUMMARIZATION_TEMPLATE
from reasoning.factory import build_research_reasoning_service
from reasoning.research_reasoning_service import ResearchResult


class SummarizationAgent(BaseAgent):
    name = "summarization_agent"

    def validate_input(self, context: TaskContext) -> None:
        for key in ("db", "user_id"):
            if key not in context.intermediate_results:
                raise ValidationAppError(f"SummarizationAgent requires '{key}' in intermediate_results")

    def execute(self, context: TaskContext) -> ResearchResult:
        db = context.intermediate_results["db"]
        user_id = context.intermediate_results["user_id"]
        # A summarization request may have no specific "question" — default
        # to a generic topic-retrieval query scoped by document_id instead.
        query = context.intermediate_results.get("query", "summary of the document's key points")
        document_id = context.intermediate_results.get("document_id")
        llm_backend = context.intermediate_results.get("llm_backend")

        service = build_research_reasoning_service(db, user_id=user_id, llm_backend=llm_backend)
        result = service.run(
            user_id=user_id,
            query=query,
            template=SUMMARIZATION_TEMPLATE,
            document_id=document_id,
            include_synthesis=False,
            similarity_threshold=context.intermediate_results.get("similarity_threshold"),
        )
        context.intermediate_results["summarization_result"] = result
        return result

    def validate_output(self, output: ResearchResult) -> None:
        if output.used_llm and output.answer is None:
            raise ValidationAppError("SummarizationAgent reported used_llm=True but produced no summary")
