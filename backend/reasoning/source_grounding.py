"""
reasoning/source_grounding.py — SOURCE GROUNDING

WHY THIS FILE EXISTS
---------------------
See docs/Phase6.md Section 4. The post-hoc, code-level half of grounding
enforcement (the prompt-level half is `PromptTemplate`'s grounding
constraint instruction). This is the verifiable half: every `chunk_id` the
model claims to have used in `sources_used` is checked against the actual
set of chunk_ids in the `AssembledContext` that was sent to it. This
cannot be fooled by a model that ignores its instructions — it's a set
membership check on data this project controls, not a request to the
model to behave.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.exceptions import GroundingViolationError
from llm.prompts.templates import StructuredAnswer
from reasoning.context_assembler import AssembledContext


@dataclass
class GroundingReport:
    is_grounded: bool
    verified_chunk_ids: list[str] = field(default_factory=list)
    fabricated_chunk_ids: list[str] = field(default_factory=list)


class SourceGrounding:
    def verify(self, answer: StructuredAnswer, context: AssembledContext, *, strict: bool = True) -> GroundingReport:
        """
        Checks every `sources_used[].chunk_id` in `answer` against
        `context`'s actual provided chunk/memory IDs.

        `strict=True` (the default, and what `ResearchReasoningService`
        uses) raises `GroundingViolationError` on any fabricated
        reference. `strict=False` returns a report instead — used by
        `CitationAgent` (Section 14), which exists specifically to
        *analyze* grounding for an already-produced answer rather than
        gate a live pipeline on it.
        """
        provided_ids = set(context.chunk_ids()) | set(context.memory_ids())
        cited_ids = [s.chunk_id for s in answer.sources_used]

        verified = [cid for cid in cited_ids if cid in provided_ids]
        fabricated = [cid for cid in cited_ids if cid not in provided_ids]

        report = GroundingReport(is_grounded=len(fabricated) == 0, verified_chunk_ids=verified, fabricated_chunk_ids=fabricated)

        if strict and fabricated:
            raise GroundingViolationError(
                f"Model response cited {len(fabricated)} source(s) that were never part of its "
                f"provided context: {fabricated}",
                details={"fabricated_chunk_ids": fabricated},
            )

        return report
