"""
reasoning/context_assembler.py — THE CONTEXT LAYER

WHY THIS FILE EXISTS
---------------------
See docs/Phase6.md Section 6. Collects retrieval + memory context exactly
like `orchestration/context_builder.py::ContextBuilder` (Phase 5) does —
calling `SemanticSearchService` and `MemoryManager` unmodified — then adds
the four LLM-specific steps `ContextBuilder` never needed: ranking (reused
from `retrieval/ranking.py`), duplicate removal (same), token budgeting,
and compression. This is intentionally a DIFFERENT class from
`ContextBuilder`, not a subclass or a modification of it — `ContextBuilder`
serves the Supervisor's general orchestration needs (Phase 5), this serves
the LLM prompt's specific needs (a bounded token budget, a flat ranked
list rather than a general-purpose bundle). Forcing one class to serve
both would couple two call sites that should be free to evolve
independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from document_processing.nlp_preprocessor import count_words
from retrieval.ranking import RankedResult, RetrievalCandidate, rank_candidates
from services.memory_manager import MemoryManager
from services.semantic_search_service import SemanticSearchService


@dataclass
class ContextItem:
    """One piece of assembled context — either a document chunk or a memory, unified for prompt rendering."""

    source_type: str  # "document_chunk" | "memory"
    source_id: str
    title: str
    text: str
    relevance_score: float
    was_compressed: bool = False


@dataclass
class AssembledContext:
    query: str
    items: list[ContextItem] = field(default_factory=list)
    excluded_count: int = 0
    excluded_reasons: dict[str, int] = field(default_factory=dict)  # reason -> count
    approx_token_count: int = 0

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0

    def chunk_ids(self) -> list[str]:
        return [item.source_id for item in self.items if item.source_type == "document_chunk"]

    def memory_ids(self) -> list[str]:
        return [item.source_id for item in self.items if item.source_type == "memory"]

    def render_for_prompt(self) -> str:
        """Renders assembled items as a numbered, source-tagged block for the prompt body."""
        if self.is_empty:
            return "(No relevant context was found.)"
        lines = []
        for i, item in enumerate(self.items, start=1):
            lines.append(f"[Source {i} | chunk_id={item.source_id} | {item.title}]\n{item.text}")
        return "\n\n".join(lines)


class ContextAssembler:
    def __init__(self, *, search_service: SemanticSearchService, memory_manager: MemoryManager) -> None:
        self.search_service = search_service
        self.memory_manager = memory_manager

    def assemble(
        self,
        *,
        user_id: UUID,
        query: str,
        token_budget: int,
        top_k_documents: int = 8,
        top_k_memory: int = 5,
        document_id: UUID | None = None,
        similarity_threshold: float = 0.0,
    ) -> AssembledContext:
        document_hits = self.search_service.search(
            query=query,
            top_k=top_k_documents,
            similarity_threshold=similarity_threshold,
            owner_id=user_id,
            document_id=document_id,
        )
        memory_hits = self.memory_manager.search(
            query=query, user_id=user_id, top_k=top_k_memory, similarity_threshold=similarity_threshold
        )

        candidates = [
            RetrievalCandidate(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_title=r.document_title,
                chunk_text=r.chunk_text,
                page_number=r.page_number,
                chunk_index=r.chunk_index,
                similarity_score=r.similarity_score,
            )
            for r in document_hits
        ] + [
            RetrievalCandidate(
                chunk_id=m.chunk_id,  # memory ID, reusing the same field per retrieval/ranking.py's generic shape
                document_id=m.chunk_id,
                document_title=f"[memory] {m.reason.split(' with')[0] if m.reason else 'memory'}",
                chunk_text=m.chunk_text,
                page_number=None,
                chunk_index=0,
                similarity_score=m.similarity_score,
            )
            for m in memory_hits
        ]

        ranked = rank_candidates(
            candidates, top_k=len(candidates), similarity_threshold=similarity_threshold, deduplicate=True
        )
        return self._apply_token_budget(query, ranked, memory_hits, token_budget)

    def _apply_token_budget(
        self,
        query: str,
        ranked: list[RankedResult],
        memory_hits: list,
        token_budget: int,
    ) -> AssembledContext:
        memory_chunk_ids = {m.chunk_id for m in memory_hits}

        context = AssembledContext(query=query)
        remaining_budget = token_budget

        for result in ranked:
            source_type = "memory" if result.chunk_id in memory_chunk_ids else "document_chunk"
            text = result.chunk_text
            text_tokens = count_words(text)

            if remaining_budget <= 0:
                context.excluded_count += 1
                context.excluded_reasons["token_budget_exhausted"] = (
                    context.excluded_reasons.get("token_budget_exhausted", 0) + 1
                )
                continue

            was_compressed = False
            if text_tokens > remaining_budget:
                # Compression (Section 6, step 4): truncate to the
                # remaining budget rather than drop entirely — a partial
                # highest-relevance chunk beats no chunk at all.
                words = text.split()
                text = " ".join(words[:remaining_budget])
                text_tokens = remaining_budget
                was_compressed = True

            context.items.append(
                ContextItem(
                    source_type=source_type,
                    source_id=result.chunk_id,
                    title=result.document_title,
                    text=text,
                    relevance_score=result.similarity_score,
                    was_compressed=was_compressed,
                )
            )
            remaining_budget -= text_tokens
            context.approx_token_count += text_tokens

        return context
