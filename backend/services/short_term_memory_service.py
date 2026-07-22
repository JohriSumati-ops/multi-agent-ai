"""
services/short_term_memory_service.py — Phase 4

WHY THIS FILE EXISTS
---------------------
Implements `memory/interfaces.py::ShortTermMemory` for real — Phase 1
defined the interface and left it unimplemented until now. Backs the
"recent conversation history, recent searches, recent uploaded documents,
recent retrievals, configurable size" requirements from the Phase 4 brief,
all as `Memory` rows with `memory_type=SHORT_TERM` and a real `expires_at`.

WHY ONE SERVICE HANDLES ALL FOUR CATEGORIES
--------------------------------------------------
Conversations, searches, uploads, and retrievals are all, at the storage
level, identical: a timestamped piece of text scoped to a user, with an
expiry. The typed `record_*` convenience methods below exist for caller
ergonomics (and to keep each call site's intent self-documenting) but all
funnel through the same `write()`/size-cap logic — duplicating four
near-identical service classes for four content types would be the kind of
copy-paste Phase 1's `BaseRepository` was specifically designed to avoid
(see repositories/base_repository.py's docstring for the same rationale
applied one layer down).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import settings
from memory.interfaces import ShortTermMemory
from models.memory import Memory, MemoryType
from repositories.memory_repository import MemoryRepository


class ShortTermMemoryService(ShortTermMemory):
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MemoryRepository(db)

    # ------------------------------------------------------------------ #
    # memory/interfaces.py::BaseMemoryStore contract
    # ------------------------------------------------------------------ #
    def write(self, user_id: UUID, content: str, *, importance_score: float = 0.5, **scope) -> Memory:
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.SHORT_TERM_MEMORY_TTL_DAYS)
        memory = Memory(
            user_id=user_id,
            memory_type=MemoryType.SHORT_TERM,
            content=content,
            importance_score=importance_score,
            expires_at=expires_at,
            conversation_id=scope.get("conversation_id"),
            document_id=scope.get("document_id"),
        )
        created = self.repo.create(memory)
        self._enforce_size_cap(user_id)
        return created

    def read(self, user_id: UUID, **filters) -> list[Memory]:
        limit = filters.get("limit", settings.SHORT_TERM_MEMORY_MAX_ITEMS)
        return self.repo.list_active(user_id, MemoryType.SHORT_TERM, limit=limit)

    # ------------------------------------------------------------------ #
    # Typed convenience recorders — see module docstring for why these
    # all funnel through write() rather than being separate storage paths.
    # ------------------------------------------------------------------ #
    def record_conversation_turn(self, user_id: UUID, conversation_id: UUID, content: str) -> Memory:
        return self.write(user_id, content, conversation_id=conversation_id)

    def record_search(self, user_id: UUID, query: str) -> Memory:
        return self.write(user_id, f"Searched: {query}")

    def record_upload(self, user_id: UUID, document_id: UUID, title: str) -> Memory:
        return self.write(user_id, f"Uploaded: {title}", document_id=document_id)

    def record_retrieval(self, user_id: UUID, query: str, result_count: int) -> Memory:
        return self.write(user_id, f"Retrieved {result_count} result(s) for: {query}")

    # ------------------------------------------------------------------ #
    # Size cap enforcement ("efficient pruning")
    # ------------------------------------------------------------------ #
    def _enforce_size_cap(self, user_id: UUID) -> int:
        """
        Keeps only the newest `SHORT_TERM_MEMORY_MAX_ITEMS` entries per
        user, deleting the rest in one query (see
        MemoryRepository.delete_excess_for_type's docstring for why this
        avoids an unbounded fetch-then-filter).
        """
        return self.repo.delete_excess_for_type(
            user_id, MemoryType.SHORT_TERM, keep_newest_n=settings.SHORT_TERM_MEMORY_MAX_ITEMS
        )
