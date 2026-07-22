"""
models/memory_access_log.py — Phase 4

WHY THIS MODEL EXISTS
-----------------------
Mirrors `models/agent_execution_log.py`'s shape: structured, queryable
telemetry rather than unstructured log lines. Every time a memory is
written or read, one row here records it — this is what
`MemoryStatisticsService` aggregates for "most accessed memories" and what
`MemoryCleanupService` uses as an LRU-style signal ("this long-term memory
hasn't been accessed in 6 months, it's a pruning candidate") that a plain
`created_at` timestamp can't provide on its own.

HOW THIS PREPARES FOR PHASE 5+
-----------------------------------
A future Recommendation/Gap-Analysis Agent (explicitly out of scope for
this phase) is the natural consumer of "which topics does this user keep
revisiting" — this table is the raw signal, not the analysis; Phase 4
itself only writes it and exposes simple aggregate counts.
"""

from __future__ import annotations

import enum

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MemoryAccessType(str, enum.Enum):
    WRITE = "write"
    READ = "read"
    SEARCH_HIT = "search_hit"  # this memory was returned by a semantic search


class MemoryAccessLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "memory_access_logs"

    memory_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memory.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_type: Mapped[MemoryAccessType] = mapped_column(nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MemoryAccessLog memory_id={self.memory_id} type={self.access_type}>"
