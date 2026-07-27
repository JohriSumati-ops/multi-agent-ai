"""
agents/reasoning_agent.py — Phase 6

WHY THIS FILE EXISTS
---------------------
Standalone access to `reasoning/research_synthesis.py`'s evidence
analysis (conflict detection, consensus notes) for a caller that wants
evidence ANALYSIS without necessarily wanting a natural-language answer
synthesized from it — e.g., a future Gap Analysis Agent deciding whether
a topic's sources are contested before deciding how to present it. Makes
NO LLM call, exactly like `CitationAgent` — this agent's entire value is
the deterministic, inspectable heuristic in `research_synthesis.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.config import settings
from core.exceptions import ValidationAppError
from reasoning.context_assembler import AssembledContext
from reasoning.factory import build_context_assembler
from reasoning.research_synthesis import SynthesisResult, synthesize


@dataclass
class ReasoningAgentResult:
    synthesis: SynthesisResult
    context: AssembledContext


class ReasoningAgent(BaseAgent):
    name = "reasoning_agent"

    def validate_input(self, context: TaskContext) -> None:
        for key in ("db", "user_id", "query"):
            if key not in context.intermediate_results:
                raise ValidationAppError(f"ReasoningAgent requires '{key}' in intermediate_results")

    def execute(self, context: TaskContext) -> ReasoningAgentResult:
        db = context.intermediate_results["db"]
        user_id: UUID = context.intermediate_results["user_id"]
        query: str = context.intermediate_results["query"]
        document_id = context.intermediate_results.get("document_id")

        assembler = build_context_assembler(db)
        assembled = assembler.assemble(
            user_id=user_id,
            query=query,
            token_budget=settings.LLM_CONTEXT_TOKEN_BUDGET,
            document_id=document_id,
            similarity_threshold=context.intermediate_results.get("similarity_threshold", settings.RETRIEVAL_SIMILARITY_THRESHOLD),
        )
        synthesis = synthesize(assembled.items)

        result = ReasoningAgentResult(synthesis=synthesis, context=assembled)
        context.intermediate_results["reasoning_result"] = result
        return result

    def validate_output(self, output: ReasoningAgentResult) -> None:
        if output.synthesis is None:
            raise ValidationAppError("ReasoningAgent produced no synthesis result")
