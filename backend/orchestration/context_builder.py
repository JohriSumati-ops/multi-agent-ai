"""
orchestration/context_builder.py — THE CONTEXT BUILDER

WHY THIS FILE EXISTS
---------------------
Before the Supervisor can plan anything, it needs to know what's already
known. This module collects that into one `ExecutionContext` by calling
Phase 3/4's EXISTING services (`MemoryManager`, `SemanticSearchService`)
— it contains no memory or retrieval logic of its own, per this project's
established "reuse, don't duplicate" rule (Phase 4's embedding-logic
reuse, extended here).

WHY EACH SOURCE IS COLLECTED, EVEN WHEN SOME WILL BE EMPTY
------------------------------------------------------------------
A brand-new user with no documents and no history will have an
`ExecutionContext` with empty memory/retrieval sections — this is
expected and correct, not an error. The `ContextBuilder`'s job is to ask
every available source, not to guarantee non-empty results; what it DOES
guarantee is that the Supervisor never has to know how to call
`MemoryManager` or `SemanticSearchService` directly — see Section 6 of
docs/Phase5.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from services.memory_manager import MemoryManager
from services.semantic_search_service import SemanticSearchService
from services.working_memory_service import WorkingMemoryService


@dataclass
class ExecutionContext:
    """
    The single unified bundle of "everything known" for one Supervisor
    invocation — exactly what docs/Phase5.md Section 6 describes.
    """

    user_id: str
    request_text: str
    working_memory_snapshot: dict = field(default_factory=dict)
    short_term_memories: list[str] = field(default_factory=list)  # recent memory content strings
    long_term_memory_hits: list[str] = field(default_factory=list)  # semantically relevant memory content
    retrieved_chunks: list[dict] = field(default_factory=list)  # document chunks relevant to the request
    conversation_history: list[dict] = field(default_factory=list)
    relevant_document_ids: list[str] = field(default_factory=list)

    def source_summary(self) -> dict[str, int]:
        """Used by the explainability layer to report which sources contributed and how much."""
        return {
            "working_memory_keys": len(self.working_memory_snapshot),
            "short_term_memories": len(self.short_term_memories),
            "long_term_memory_hits": len(self.long_term_memory_hits),
            "retrieved_chunks": len(self.retrieved_chunks),
            "conversation_turns": len(self.conversation_history),
        }


class ContextBuilder:
    def __init__(
        self,
        *,
        working_memory: WorkingMemoryService,
        memory_manager: MemoryManager,
        search_service: SemanticSearchService,
    ) -> None:
        self.working_memory = working_memory
        self.memory_manager = memory_manager
        self.search_service = search_service

    def build(
        self,
        *,
        user_id: UUID,
        request_text: str,
        top_k_memory: int = 5,
        top_k_documents: int = 5,
        document_id: UUID | None = None,
    ) -> ExecutionContext:
        short_term = self.memory_manager.short_term.read(user_id, limit=10)
        long_term_hits = self.memory_manager.search(
            query=request_text, user_id=user_id, top_k=top_k_memory, similarity_threshold=0.0
        )
        document_hits = self.search_service.search(
            query=request_text,
            top_k=top_k_documents,
            similarity_threshold=0.0,
            owner_id=user_id,
            document_id=document_id,
        )

        return ExecutionContext(
            user_id=str(user_id),
            request_text=request_text,
            working_memory_snapshot=self.working_memory.snapshot(),
            short_term_memories=[m.content for m in short_term],
            long_term_memory_hits=[r.chunk_text for r in long_term_hits],
            retrieved_chunks=[
                {
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "chunk_text": r.chunk_text,
                    "similarity_score": r.similarity_score,
                }
                for r in document_hits
            ],
            relevant_document_ids=list({r.document_id for r in document_hits}),
        )
