"""
agents/question_answering_agent.py — Phase 6

WHY THIS FILE EXISTS
---------------------
Narrower than `ResearchAgent`: answers a specific question, typically
scoped to one document (`document_id` is expected, not just optional),
using `QUESTION_ANSWERING_TEMPLATE` (a stricter, more focused system
instruction than the open-ended research template) and skipping
multi-document synthesis (`include_synthesis=False`) — a single-document
question has no cross-source conflicts to detect.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError
from llm.prompts.templates import QUESTION_ANSWERING_TEMPLATE
from reasoning.factory import build_research_reasoning_service
from reasoning.research_reasoning_service import ResearchResult


class QuestionAnsweringAgent(BaseAgent):
    name = "question_answering_agent"

    def validate_input(self, context: TaskContext) -> None:
        for key in ("db", "user_id", "query"):
            if key not in context.intermediate_results:
                raise ValidationAppError(f"QuestionAnsweringAgent requires '{key}' in intermediate_results")

    def execute(self, context: TaskContext) -> ResearchResult:
        db = context.intermediate_results["db"]
        user_id = context.intermediate_results["user_id"]
        query = context.intermediate_results["query"]
        document_id = context.intermediate_results.get("document_id")
        llm_backend = context.intermediate_results.get("llm_backend")

        service = build_research_reasoning_service(db, user_id=user_id, llm_backend=llm_backend)
        result = service.run(
            user_id=user_id,
            query=query,
            template=QUESTION_ANSWERING_TEMPLATE,
            document_id=document_id,
            include_synthesis=False,
            similarity_threshold=context.intermediate_results.get("similarity_threshold"),
        )
        context.intermediate_results["qa_result"] = result
        return result

    def validate_output(self, output: ResearchResult) -> None:
        if output.used_llm and output.answer is None:
            raise ValidationAppError("QuestionAnsweringAgent reported used_llm=True but produced no answer")
