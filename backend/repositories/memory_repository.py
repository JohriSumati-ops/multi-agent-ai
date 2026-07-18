"""
repositories/memory_repository.py

Storage-layer access for the Memory table. Note this repository does NOT
decide what's worth remembering or how it should be weighted for retrieval
— that policy lives in memory/interfaces.py's future implementations. This
repository only knows how to persist and fetch rows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.memory import Memory, MemoryType
from repositories.base_repository import BaseRepository


class MemoryRepository(BaseRepository[Memory]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Memory)

    def list_by_type(
        self, user_id: UUID, memory_type: MemoryType, *, limit: int = 50
    ) -> list[Memory]:
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id, Memory.memory_type == memory_type)
            .order_by(Memory.importance_score.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_active(self, user_id: UUID, memory_type: MemoryType, *, limit: int = 50) -> list[Memory]:
        """Same as list_by_type but excludes expired short-term entries."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.memory_type == memory_type,
                (Memory.expires_at.is_(None)) | (Memory.expires_at > now),
            )
            .order_by(Memory.importance_score.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
