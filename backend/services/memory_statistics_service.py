"""
services/memory_statistics_service.py — Phase 4

WHY THIS FILE EXISTS
---------------------
Aggregation-only — no writes happen here. Backs `GET /memory/statistics`
with counts by memory type, total access volume, the most-accessed
memories (an early, cheap signal a future Recommendation Agent could use),
and a simple "memory health" indicator (the ratio of expired-but-not-yet-
pruned short-term memories, which should stay near zero if
`MemoryCleanupService` is running regularly).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from repositories.memory_access_log_repository import MemoryAccessLogRepository
from repositories.memory_repository import MemoryRepository


class MemoryStatisticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.memory_repo = MemoryRepository(db)
        self.access_log_repo = MemoryAccessLogRepository(db)

    def get_statistics(self, user_id: UUID) -> dict:
        counts_by_type = self.memory_repo.count_by_type(user_id)
        total_memories = sum(counts_by_type.values())
        total_accesses = self.access_log_repo.count_accesses_for_user(user_id)
        expired_pending_cleanup = len(self.memory_repo.list_expired(limit=10_000))

        most_accessed = self.access_log_repo.most_accessed_memory_ids(user_id, limit=5)
        most_accessed_ids = [str(memory_id) for memory_id, _count in most_accessed]

        return {
            "total_memories": total_memories,
            "counts_by_type": counts_by_type,
            "total_accesses": total_accesses,
            "expired_pending_cleanup": expired_pending_cleanup,
            "most_accessed_memory_ids": most_accessed_ids,
            "memory_health": "healthy" if expired_pending_cleanup == 0 else "cleanup_recommended",
        }
