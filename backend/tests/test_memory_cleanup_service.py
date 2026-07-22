"""
tests/test_memory_cleanup_service.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from models.memory import MemoryType
from models.memory_access_log import MemoryAccessType
from models.user import User
from repositories.memory_access_log_repository import MemoryAccessLogRepository
from repositories.memory_repository import MemoryRepository
from services.long_term_memory_service import LongTermMemoryService
from services.memory_cleanup_service import MemoryCleanupService, _as_utc
from services.short_term_memory_service import ShortTermMemoryService


def _make_user(db_session) -> User:
    user = User(email="cleanup@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_as_utc_normalizes_naive_datetime() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)
    result = _as_utc(naive)
    assert result.tzinfo is not None


def test_as_utc_leaves_aware_datetime_unchanged() -> None:
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert _as_utc(aware) is aware


def test_cleanup_expired_removes_only_expired_memories(db_session) -> None:
    user = _make_user(db_session)
    repo = MemoryRepository(db_session)

    stm = ShortTermMemoryService(db_session)
    fresh = stm.write(user.id, "still fresh")
    expired = stm.write(user.id, "already expired")
    expired.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    repo.commit_refresh(expired)

    # Capture IDs before running cleanup: MemoryCleanupService.cleanup_expired()
    # commits, which expires every object in this session (SQLAlchemy's
    # default expire_on_commit=True) — the deleted row can no longer be
    # reloaded afterward, so accessing `expired.id` post-cleanup would
    # correctly raise ObjectDeletedError. Capturing IDs first sidesteps that.
    fresh_id, expired_id = fresh.id, expired.id

    deleted = MemoryCleanupService(db_session).cleanup_expired()
    assert deleted == 1
    assert repo.get(fresh_id) is not None
    assert repo.get(expired_id) is None


def test_prune_over_cap_removes_lowest_importance_and_their_vectors(db_session) -> None:
    user = _make_user(db_session)
    ltm = LongTermMemoryService(db_session)
    ltm.write(user.id, "high value insight", importance_score=0.9)
    low_value = ltm.write(user.id, "low value insight", importance_score=0.1)

    assert ltm.vector_store.ntotal == 2

    cleanup = MemoryCleanupService(db_session)
    pruned = cleanup.prune_over_cap(user.id, keep_top_n=1)

    assert pruned == 1
    assert cleanup.repo.get(low_value.id) is None
    assert cleanup.embedding_repo.get_by_memory_id(low_value.id) is None
    assert ltm.vector_store.ntotal == 1


def test_prune_over_cap_no_op_when_under_cap(db_session) -> None:
    user = _make_user(db_session)
    LongTermMemoryService(db_session).write(user.id, "only insight")

    pruned = MemoryCleanupService(db_session).prune_over_cap(user.id, keep_top_n=10)
    assert pruned == 0


def test_archive_low_value_memories_demotes_importance(db_session) -> None:
    user = _make_user(db_session)
    ltm = LongTermMemoryService(db_session)
    memory = ltm.write(user.id, "stale insight", importance_score=0.8)

    repo = MemoryRepository(db_session)
    memory.created_at = datetime.now(timezone.utc) - timedelta(days=200)
    repo.commit_refresh(memory)

    archived = MemoryCleanupService(db_session).archive_low_value_memories(user.id, inactivity_days=180)
    assert archived == 1
    refreshed = repo.get(memory.id)
    assert refreshed.importance_score == 0.1


def test_archive_low_value_memories_skips_recent_memories(db_session) -> None:
    user = _make_user(db_session)
    LongTermMemoryService(db_session).write(user.id, "fresh insight", importance_score=0.8)

    archived = MemoryCleanupService(db_session).archive_low_value_memories(user.id, inactivity_days=180)
    assert archived == 0


def test_archive_low_value_memories_uses_last_access_time_when_available(db_session) -> None:
    user = _make_user(db_session)
    ltm = LongTermMemoryService(db_session)
    memory = ltm.write(user.id, "recently re-accessed insight", importance_score=0.8)

    repo = MemoryRepository(db_session)
    memory.created_at = datetime.now(timezone.utc) - timedelta(days=200)
    repo.commit_refresh(memory)

    # A recent access should override the old created_at as the reference point.
    MemoryAccessLogRepository(db_session).log_access(memory.id, user.id, MemoryAccessType.READ)

    archived = MemoryCleanupService(db_session).archive_low_value_memories(user.id, inactivity_days=180)
    assert archived == 0  # recently accessed -> not archived despite old created_at


def test_run_full_cleanup_returns_all_three_counts(db_session) -> None:
    user = _make_user(db_session)
    result = MemoryCleanupService(db_session).run_full_cleanup(user.id, keep_top_n_long_term=1000)
    assert set(result.keys()) == {"expired_deleted", "over_cap_pruned", "archived"}
