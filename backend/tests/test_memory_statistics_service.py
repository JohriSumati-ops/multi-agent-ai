"""
tests/test_memory_statistics_service.py
"""

from __future__ import annotations

from models.user import User
from services.long_term_memory_service import LongTermMemoryService
from services.memory_statistics_service import MemoryStatisticsService
from services.short_term_memory_service import ShortTermMemoryService


def _make_user(db_session) -> User:
    user = User(email="stats@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_statistics_for_user_with_no_memory(db_session) -> None:
    user = _make_user(db_session)
    stats = MemoryStatisticsService(db_session).get_statistics(user.id)

    assert stats["total_memories"] == 0
    assert stats["counts_by_type"] == {}
    assert stats["memory_health"] == "healthy"


def test_statistics_counts_by_type(db_session) -> None:
    user = _make_user(db_session)
    ShortTermMemoryService(db_session).write(user.id, "recent thing")
    LongTermMemoryService(db_session).write(user.id, "durable insight")
    LongTermMemoryService(db_session).write(user.id, "another insight")

    stats = MemoryStatisticsService(db_session).get_statistics(user.id)
    assert stats["total_memories"] == 3
    assert stats["counts_by_type"]["short_term"] == 1
    assert stats["counts_by_type"]["long_term"] == 2


def test_statistics_reports_expired_pending_cleanup(db_session) -> None:
    from datetime import datetime, timedelta, timezone

    from repositories.memory_repository import MemoryRepository

    user = _make_user(db_session)
    repo = MemoryRepository(db_session)
    memory = ShortTermMemoryService(db_session).write(user.id, "will expire")
    memory.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    repo.commit_refresh(memory)

    stats = MemoryStatisticsService(db_session).get_statistics(user.id)
    assert stats["expired_pending_cleanup"] == 1
    assert stats["memory_health"] == "cleanup_recommended"


def test_statistics_most_accessed_reflects_search_hits(db_session) -> None:
    from services.memory_search_service import MemorySearchService

    user = _make_user(db_session)
    memory = LongTermMemoryService(db_session).write(user.id, "frequently searched insight")

    search_service = MemorySearchService(db_session)
    search_service.search(query="frequently searched", user_id=user.id, similarity_threshold=-1.0)
    search_service.search(query="frequently searched", user_id=user.id, similarity_threshold=-1.0)

    stats = MemoryStatisticsService(db_session).get_statistics(user.id)
    assert str(memory.id) in stats["most_accessed_memory_ids"]
    assert stats["total_accesses"] == 2
