"""
repositories/memory_repository.py

Storage-layer access for the Memory table. Note this repository does NOT
decide what's worth remembering or how it should be weighted for retrieval
— that policy lives in memory/interfaces.py's implementations and the
services/ layer. This repository only knows how to persist and fetch rows.

PHASE 4 UPDATE (additive only — no existing method changed)
------------------------------------------------------------------
Added query methods needed by the new memory services: recall across all
types (`list_recent_for_user`), cleanup support (`list_expired`,
`delete_expired`), statistics support (`count_by_type`), and bulk lookup
for semantic search result resolution (`get_by_ids`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
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

    def list_recent_for_user(
        self, user_id: UUID, *, memory_type: MemoryType | None = None, limit: int = 20
    ) -> list[Memory]:
        """
        Phase 4: recall across all (or one) memory type, ordered purely by
        recency — backs `GET /memory/recent`, which cares about "what
        just happened" rather than importance-weighted ranking.
        """
        now = datetime.now(timezone.utc)
        conditions = [
            Memory.user_id == user_id,
            (Memory.expires_at.is_(None)) | (Memory.expires_at > now),
        ]
        if memory_type is not None:
            conditions.append(Memory.memory_type == memory_type)

        stmt = select(Memory).where(*conditions).order_by(Memory.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def list_expired(self, *, limit: int = 1000) -> list[Memory]:
        """Phase 4: used by MemoryCleanupService to find expired short-term entries to prune."""
        now = datetime.now(timezone.utc)
        stmt = select(Memory).where(Memory.expires_at.is_not(None), Memory.expires_at <= now).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def delete_expired(self) -> int:
        """
        Bulk-delete expired memories. Returns the number of rows deleted.

        Uses `synchronize_session=False`: by default, SQLAlchemy's ORM
        DELETE tries to keep the in-memory session consistent by
        re-evaluating the WHERE clause in Python against already-loaded
        objects. That Python-side evaluation compares
        `Memory.expires_at <= now` directly — and hit the exact
        naive-vs-aware datetime comparison bug documented in
        `services/memory_cleanup_service.py`'s `_as_utc` helper (SQLite
        returns naive datetimes for `TIMESTAMP(timezone=True)` columns).
        `synchronize_session=False` lets the database itself evaluate the
        WHERE clause (which handles the comparison correctly in both
        PostgreSQL and SQLite) instead of re-evaluating it in Python.
        """
        now = datetime.now(timezone.utc)
        stmt = delete(Memory).where(Memory.expires_at.is_not(None), Memory.expires_at <= now)
        result = self.db.execute(stmt, execution_options={"synchronize_session": False})
        self.db.commit()
        return result.rowcount or 0

    def count_by_type(self, user_id: UUID) -> dict[str, int]:
        """Phase 4: backs MemoryStatisticsService — one grouped query instead of N count() calls."""
        stmt = (
            select(Memory.memory_type, func.count(Memory.id))
            .where(Memory.user_id == user_id)
            .group_by(Memory.memory_type)
        )
        return {mtype.value: count for mtype, count in self.db.execute(stmt).all()}

    def get_by_ids(self, memory_ids: list[UUID]) -> list[Memory]:
        """Bulk lookup used by MemorySearchService to resolve FAISS search hits."""
        if not memory_ids:
            return []
        stmt = select(Memory).where(Memory.id.in_(memory_ids))
        return list(self.db.execute(stmt).scalars().all())

    def list_low_importance(self, user_id: UUID, *, keep_top_n: int) -> list[Memory]:
        """
        Phase 4: used by MemoryCleanupService's over-cap pruning — returns
        every LONG_TERM memory for this user EXCEPT the `keep_top_n`
        highest-importance ones, i.e. exactly the prune candidates.
        """
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id, Memory.memory_type == MemoryType.LONG_TERM)
            .order_by(Memory.importance_score.desc(), Memory.created_at.desc())
            .offset(keep_top_n)
        )
        return list(self.db.execute(stmt).scalars().all())

    def delete_all_for_user(self, user_id: UUID) -> int:
        """Danger-zone bulk delete — backs `POST /memory/clear`."""
        stmt = delete(Memory).where(Memory.user_id == user_id)
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount or 0

    def delete_excess_for_type(self, user_id: UUID, memory_type: MemoryType, *, keep_newest_n: int) -> int:
        """
        Phase 4: efficient short-term memory size-cap enforcement.

        Rather than fetching every row and deleting in Python, this finds
        the IDs beyond the newest `keep_newest_n` (ordered by created_at
        descending) in one query and deletes exactly those — the "efficient
        pruning" the Phase 4 brief asks for, avoiding an unbounded
        SELECT-then-filter over a user's full short-term memory history.

        NOTE on ordering ties: SQLite's `CURRENT_TIMESTAMP` has only
        1-second resolution, so rapid successive writes (e.g., in a tight
        test loop, or a burst import) can share an identical `created_at`
        — discovered while testing this exact method. `id` is added as a
        secondary sort key purely to make tie-breaking deterministic
        (reproducible test behavior); it does NOT reflect true insertion
        order, since UUIDs are random. PostgreSQL's microsecond timestamp
        resolution makes this tie far less likely in production, but the
        secondary key costs nothing and removes the ambiguity either way.
        """
        excess_ids_stmt = (
            select(Memory.id)
            .where(Memory.user_id == user_id, Memory.memory_type == memory_type)
            .order_by(Memory.created_at.desc(), Memory.id.desc())
            .offset(keep_newest_n)
        )
        excess_ids = [row[0] for row in self.db.execute(excess_ids_stmt).all()]
        if not excess_ids:
            return 0

        stmt = delete(Memory).where(Memory.id.in_(excess_ids))
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount or 0
