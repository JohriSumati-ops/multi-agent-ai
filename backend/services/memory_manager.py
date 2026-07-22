"""
services/memory_manager.py — Phase 4 — THE CENTRAL ORCHESTRATOR

WHY THIS FILE EXISTS
---------------------
Everything else in this phase (`WorkingMemoryService`, `ShortTermMemoryService`,
`LongTermMemoryService`, `SessionMemoryService`, `MemorySearchService`,
`MemoryCleanupService`, `MemoryStatisticsService`) is a focused, single-
responsibility component. `MemoryManager` is the one object that composes
all of them behind a single interface — this is exactly the facade
`docs/Phase4.md` Section 7 describes as what a future Supervisor Agent
will depend on, so that by the time a Supervisor exists, it calls one
object instead of needing to know seven different memory services exist
individually. `api/routes/memory.py` is the first real consumer of that
facade.

CONFLICT RESOLUTION
-----------------------
"Conflict resolution," concretely, means: writing an exact duplicate of an
existing memory should update that memory (refresh its recency /
importance) rather than silently accumulating duplicate rows forever. This
is checked via an in-Python exact-match comparison over the user's current
short-term or long-term memory set (already small and bounded — see
`services/short_term_memory_service.py`'s size-cap enforcement and
`settings.LONG_TERM_MEMORY_MAX_ITEMS`) rather than a new indexed database
query, which is a reasonable tradeoff at this scale and avoids adding
schema (a unique constraint on content would be too strict — two
genuinely different memories can coincidentally share text, e.g. two
different conversations both containing "explain trees").

MEMORY LIFECYCLE MANAGEMENT
--------------------------------
`MemoryManager` is also where the four memory types' *relationships* to
each other are expressed: a `remember()` call can simultaneously write to
short-term memory (so it shows up in "recent activity" immediately) and,
when explicitly flagged `persist_long_term=True`, also promote it to
long-term, semantically-indexed memory — the write path shown in
docs/Phase4.md Section 8.1.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from models.memory import Memory, MemoryType
from repositories.memory_repository import MemoryRepository
from retrieval.ranking import RankedResult
from services.long_term_memory_service import LongTermMemoryService
from services.memory_cleanup_service import MemoryCleanupService
from services.memory_search_service import MemorySearchService
from services.memory_statistics_service import MemoryStatisticsService
from services.session_memory_service import SessionMemoryService
from services.short_term_memory_service import ShortTermMemoryService
from services.working_memory_service import WorkingMemoryService


class MemoryManager:
    def __init__(self, db: Session, *, working_memory: WorkingMemoryService | None = None) -> None:
        self.db = db
        self.repo = MemoryRepository(db)

        # `working_memory` is injected rather than constructed here because
        # it must be the SAME instance the request's other dependencies
        # share (see api/deps.py) — constructing a new one here would
        # silently defeat working memory's purpose (nothing else in the
        # request could ever read what was written to it).
        self.working = working_memory or WorkingMemoryService()
        self.short_term = ShortTermMemoryService(db)
        self.long_term = LongTermMemoryService(db)
        self.session = SessionMemoryService()
        self.search_service = MemorySearchService(db)
        self.cleanup_service = MemoryCleanupService(db)
        self.statistics_service = MemoryStatisticsService(db)

    # ------------------------------------------------------------------ #
    # Unified write path
    # ------------------------------------------------------------------ #
    def remember(
        self,
        user_id: UUID,
        content: str,
        *,
        persist_long_term: bool = False,
        importance_score: float = 0.5,
        conversation_id: UUID | None = None,
        document_id: UUID | None = None,
    ) -> Memory:
        """
        Writes to short-term memory (always) and, if `persist_long_term`,
        also to long-term memory (semantically indexed). See module
        docstring's "Conflict Resolution" section for the dedup check
        applied before either write.
        """
        existing = self._find_exact_duplicate(user_id, content, persist_long_term)
        if existing is not None:
            existing.importance_score = max(existing.importance_score, importance_score)
            self.repo.commit_refresh(existing)
            return existing

        scope = {}
        if conversation_id is not None:
            scope["conversation_id"] = conversation_id
        if document_id is not None:
            scope["document_id"] = document_id

        if persist_long_term:
            return self.long_term.write(user_id, content, importance_score=importance_score, **scope)
        return self.short_term.write(user_id, content, importance_score=importance_score, **scope)

    def _find_exact_duplicate(self, user_id: UUID, content: str, persist_long_term: bool) -> Memory | None:
        target_type = MemoryType.LONG_TERM if persist_long_term else MemoryType.SHORT_TERM
        candidates = self.repo.list_active(user_id, target_type, limit=200)
        normalized = content.strip().lower()
        for candidate in candidates:
            if candidate.content.strip().lower() == normalized:
                return candidate
        return None

    # ------------------------------------------------------------------ #
    # Unified read paths
    # ------------------------------------------------------------------ #
    def get_history(self, user_id: UUID, *, memory_type: MemoryType | None = None, limit: int = 20) -> list[Memory]:
        return self.repo.list_recent_for_user(user_id, memory_type=memory_type, limit=limit)

    def get_recent(self, user_id: UUID, *, limit: int = 10) -> list[Memory]:
        return self.repo.list_recent_for_user(user_id, limit=limit)

    def search(self, *, query: str, user_id: UUID, top_k: int = 5, similarity_threshold: float = 0.0) -> list[RankedResult]:
        return self.search_service.search(
            query=query, user_id=user_id, top_k=top_k, similarity_threshold=similarity_threshold
        )

    def get_statistics(self, user_id: UUID) -> dict:
        return self.statistics_service.get_statistics(user_id)

    # ------------------------------------------------------------------ #
    # Session lifecycle
    # ------------------------------------------------------------------ #
    def get_session_state(self, session_id: str, user_id: UUID) -> dict:
        return self.session.get_session_state(session_id, user_id)

    def end_session(self, session_id: str) -> None:
        self.session.end_session(session_id)

    # ------------------------------------------------------------------ #
    # Cleanup / deletion
    # ------------------------------------------------------------------ #
    def prune(self, user_id: UUID, *, keep_top_n_long_term: int = 1000) -> dict[str, int]:
        return self.cleanup_service.run_full_cleanup(user_id, keep_top_n_long_term=keep_top_n_long_term)

    def delete_history(self, user_id: UUID, *, memory_type: MemoryType | None = None) -> int:
        """Deletes memories matching an optional type filter — backs `DELETE /memory/history`."""
        if memory_type is None:
            return self.repo.delete_all_for_user(user_id)

        # Long-term deletions must also clean up their FAISS vectors —
        # delegate to LongTermMemoryService.delete() per-row for that type,
        # since MemoryRepository's bulk delete deliberately doesn't know
        # about the vector store (Repository Pattern boundary — see
        # repositories/base_repository.py).
        if memory_type == MemoryType.LONG_TERM:
            memories = self.repo.list_by_type(user_id, MemoryType.LONG_TERM, limit=10_000)
            for memory in memories:
                self.long_term.delete(memory.id)
            return len(memories)

        memories = self.repo.list_by_type(user_id, memory_type, limit=10_000)
        for memory in memories:
            self.repo.delete(memory)
        return len(memories)

    def clear_all(self, user_id: UUID) -> int:
        """Danger-zone: clears every memory (all types) for a user — backs `POST /memory/clear`."""
        long_term_memories = self.repo.list_by_type(user_id, MemoryType.LONG_TERM, limit=10_000)
        for memory in long_term_memories:
            self.long_term.delete(memory.id)  # also removes the FAISS vector + MemoryEmbedding row

        remaining = self.repo.delete_all_for_user(user_id)  # everything else (short-term, conversation, document)
        return len(long_term_memories) + remaining
