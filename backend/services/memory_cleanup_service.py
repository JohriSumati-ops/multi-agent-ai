"""
services/memory_cleanup_service.py — Phase 4

WHY THIS FILE EXISTS
---------------------
Expiration (Section 4 of docs/Phase4.md) is a passive property of a row
(`expires_at <= now`); pruning is the active act of removing those rows
(and, separately, trimming over-cap long-term memory by importance). This
service is where both actions live, kept distinct from `MemoryRepository`
(which only knows how to query/delete — not *when* it's appropriate to).

"ARCHIVING" NOTE
-------------------
The Phase 4 brief lists "archiving" alongside expiration/pruning. This
project has no separate cold-storage tier (no S3/blob store, no archive
table) — introducing one would be a genuine architecture addition, which
this phase's "do not redesign the architecture" constraint argues against.
`archive_low_value_memories()` here implements the achievable version of
that idea within the existing schema: demoting a long-term memory's
`importance_score` toward zero (rather than deleting it outright) for
memories that haven't been accessed in a long time, so they sink to the
bottom of every ranked query without being destroyed — a soft-delete-by-
deprioritization, not a physical archive tier. This tradeoff is
deliberate and documented here rather than silently narrowing scope.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from core.logging import get_logger
from models.memory import MemoryType
from repositories.memory_access_log_repository import MemoryAccessLogRepository
from repositories.memory_embedding_repository import MemoryEmbeddingRepository
from repositories.memory_repository import MemoryRepository
from retrieval.embedder import EmbeddingService
from retrieval.vector_store import get_memory_vector_store

logger = get_logger("app")


def _as_utc(value: datetime) -> datetime:
    """
    Normalizes a datetime to timezone-aware UTC. See
    `archive_low_value_memories`'s docstring for why this is needed:
    SQLite returns naive datetimes for `TIMESTAMP(timezone=True)` columns
    even though PostgreSQL returns aware ones for the same schema.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class MemoryCleanupService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MemoryRepository(db)
        self.embedding_repo = MemoryEmbeddingRepository(db)
        self.access_log_repo = MemoryAccessLogRepository(db)

    def cleanup_expired(self) -> int:
        """
        Deletes every short-term memory past its `expires_at`, including
        its FAISS-adjacent bookkeeping — short-term memories are never
        embedded (see LongTermMemoryService's docstring: only long-term
        memory is indexed), so this is a plain SQL delete, no vector store
        involvement needed.
        """
        deleted = self.repo.delete_expired()
        if deleted:
            logger.info("Memory cleanup: deleted %d expired short-term memories", deleted)
        return deleted

    def prune_over_cap(self, user_id: UUID, *, keep_top_n: int) -> int:
        """
        Removes the lowest-importance LONG_TERM memories beyond
        `keep_top_n` for one user — including their FAISS vectors and
        `MemoryEmbedding` rows, unlike `cleanup_expired`, since long-term
        memories ARE indexed.
        """
        candidates = self.repo.list_low_importance(user_id, keep_top_n=keep_top_n)
        if not candidates:
            return 0

        vector_store = get_memory_vector_store(dimension=EmbeddingService.get_instance().dimension)
        import numpy as np

        for memory in candidates:
            embedding = self.embedding_repo.get_by_memory_id(memory.id)
            if embedding is not None:
                vector_store.remove_vectors(np.array([embedding.vector_id], dtype=np.int64))
                self.embedding_repo.delete_by_memory_id(memory.id)
            self.repo.delete(memory)

        vector_store.save()
        logger.info("Memory cleanup: pruned %d over-cap long-term memories for user %s", len(candidates), user_id)
        return len(candidates)

    def archive_low_value_memories(self, user_id: UUID, *, inactivity_days: int = 180) -> int:
        """
        See module docstring's "Archiving" note: demotes (does not delete)
        long-term memories that haven't been accessed (per
        `MemoryAccessLog`) in `inactivity_days`, by setting their
        importance_score toward a low floor rather than removing them.

        NOTE on timezone handling: PostgreSQL returns timezone-aware
        datetimes for `TIMESTAMP(timezone=True)` columns, but SQLite (used
        in this project's test suite) silently returns naive datetimes for
        the same column type — a real gap discovered while building this
        method, not a hypothetical one. `_as_utc` normalizes both cases
        before comparison so this method behaves identically against
        either database.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=inactivity_days)
        long_term_memories = self.repo.list_by_type(user_id, MemoryType.LONG_TERM, limit=10_000)

        archived_count = 0
        for memory in long_term_memories:
            last_access_time = self.access_log_repo.get_last_access_time(memory.id)
            reference_time = _as_utc(last_access_time or memory.created_at)

            if reference_time < cutoff and memory.importance_score > 0.1:
                memory.importance_score = 0.1
                self.repo.commit_refresh(memory)
                archived_count += 1

        if archived_count:
            logger.info("Memory cleanup: archived %d low-value long-term memories for user %s", archived_count, user_id)
        return archived_count

    def run_full_cleanup(self, user_id: UUID, *, keep_top_n_long_term: int) -> dict[str, int]:
        """Convenience: runs every cleanup pass in sequence — backs `DELETE /memory/prune`."""
        return {
            "expired_deleted": self.cleanup_expired(),
            "over_cap_pruned": self.prune_over_cap(user_id, keep_top_n=keep_top_n_long_term),
            "archived": self.archive_low_value_memories(user_id),
        }
