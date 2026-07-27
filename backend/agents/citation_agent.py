"""
agents/citation_agent.py — Phase 6

WHY THIS FILE EXISTS
---------------------
Standalone access to `CitationInjector` (+ optional `SourceGrounding`
analysis) for a caller that already has a draft answer's cited chunk_ids
and needs them resolved to real citation text — e.g., a future Writing
Agent's draft, or a client re-checking an older `ResearchResponse`. Unlike
`ResearchAgent`, this agent makes NO LLM call — pure lookup/verification
against already-produced data, which is why it's registered as a distinct,
much cheaper capability (see orchestration/agent_registry.py's
registration in api/deps.py-adjacent bootstrap code).

INPUT: "db" (Session), "chunk_ids" (list[str]). Optional: "context"
(reasoning.context_assembler.AssembledContext) — when provided, also runs
a non-strict grounding check (`strict=False`: returns a report, never
raises — this agent's job is to ANALYZE, not gate a pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.exceptions import ValidationAppError
from reasoning.citation_injector import Citation
from reasoning.factory import build_citation_injector
from reasoning.source_grounding import GroundingReport, SourceGrounding


@dataclass
class CitationAgentResult:
    citations: list[Citation]
    grounding_report: GroundingReport | None = None


class CitationAgent(BaseAgent):
    name = "citation_agent"

    def validate_input(self, context: TaskContext) -> None:
        for key in ("db", "chunk_ids"):
            if key not in context.intermediate_results:
                raise ValidationAppError(f"CitationAgent requires '{key}' in intermediate_results")

    def execute(self, context: TaskContext) -> CitationAgentResult:
        db = context.intermediate_results["db"]
        chunk_ids: list[str] = context.intermediate_results["chunk_ids"]
        assembled_context = context.intermediate_results.get("context")
        answer = context.intermediate_results.get("answer")  # StructuredAnswer, only needed for grounding

        citations = build_citation_injector(db).inject(chunk_ids)

        grounding_report = None
        if assembled_context is not None and answer is not None:
            grounding_report = SourceGrounding().verify(answer, assembled_context, strict=False)

        result = CitationAgentResult(citations=citations, grounding_report=grounding_report)
        context.intermediate_results["citation_result"] = result
        return result

    def validate_output(self, output: CitationAgentResult) -> None:
        if output.citations is None:
            raise ValidationAppError("CitationAgent produced no citations list")
