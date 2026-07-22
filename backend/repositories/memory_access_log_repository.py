"""
repositories/memory_access_log_repository.py — Phase 4
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.memory_access_log import MemoryAccessLog, MemoryAccessType
from repositories.base_repository import BaseRepository


class MemoryAccessLogRepository(BaseRepository[MemoryAccessLog]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, MemoryAccessLog)

    def log_access(self, memory_id: UUID, user_id: UUID, access_type: MemoryAccessType) -> MemoryAccessLog:
        return self.create(MemoryAccessLog(memory_id=memory_id, user_id=user_id, access_type=access_type))

    def count_accesses_for_user(self, user_id: UUID) -> int:
        stmt = select(func.count(MemoryAccessLog.id)).where(MemoryAccessLog.user_id == user_id)
        return self.db.execute(stmt).scalar_one()

    def most_accessed_memory_ids(self, user_id: UUID, *, limit: int = 10) -> list[tuple[UUID, int]]:
        """Returns (memory_id, access_count) pairs, descending by access count — backs statistics."""
        stmt = (
            select(MemoryAccessLog.memory_id, func.count(MemoryAccessLog.id).label("access_count"))
            .where(MemoryAccessLog.user_id == user_id)
            .group_by(MemoryAccessLog.memory_id)
            .order_by(func.count(MemoryAccessLog.id).desc())
            .limit(limit)
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt).all()]

    def get_last_access_time(self, memory_id: UUID) -> datetime | None:
        """Most recent access timestamp for one memory, or None if never accessed."""
        stmt = (
            select(MemoryAccessLog.created_at)
            .where(MemoryAccessLog.memory_id == memory_id)
            .order_by(MemoryAccessLog.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
