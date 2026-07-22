"""
tests/test_memory_manager.py
"""

from __future__ import annotations

import uuid

from models.memory import MemoryType
from models.user import User
from services.memory_manager import MemoryManager


def _make_user(db_session) -> User:
    user = User(email="manager@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_remember_defaults_to_short_term(db_session) -> None:
    user = _make_user(db_session)
    memory = MemoryManager(db_session).remember(user.id, "default scope memory")
    assert memory.memory_type == MemoryType.SHORT_TERM


def test_remember_persists_long_term_when_flagged(db_session) -> None:
    user = _make_user(db_session)
    memory = MemoryManager(db_session).remember(user.id, "durable insight", persist_long_term=True)
    assert memory.memory_type == MemoryType.LONG_TERM
    assert memory.expires_at is None


def test_remember_deduplicates_exact_matches(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)

    first = manager.remember(user.id, "  Explained Binary Trees  ", importance_score=0.5)
    second = manager.remember(user.id, "explained binary trees", importance_score=0.8)

    assert first.id == second.id
    assert second.importance_score == 0.8  # importance updated to the higher value


def test_remember_does_not_dedupe_across_short_and_long_term(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)

    short = manager.remember(user.id, "duplicate text", persist_long_term=False)
    long_ = manager.remember(user.id, "duplicate text", persist_long_term=True)

    assert short.id != long_.id
    assert short.memory_type == MemoryType.SHORT_TERM
    assert long_.memory_type == MemoryType.LONG_TERM


def test_get_history_returns_recent_memories(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)
    manager.remember(user.id, "one")
    manager.remember(user.id, "two")

    history = manager.get_history(user.id)
    assert len(history) == 2


def test_get_history_filters_by_type(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)
    manager.remember(user.id, "short one", persist_long_term=False)
    manager.remember(user.id, "long one", persist_long_term=True)

    short_only = manager.get_history(user.id, memory_type=MemoryType.SHORT_TERM)
    assert len(short_only) == 1
    assert short_only[0].memory_type == MemoryType.SHORT_TERM


def test_search_delegates_to_search_service(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)
    manager.remember(user.id, "searchable insight", persist_long_term=True)

    results = manager.search(query="searchable insight", user_id=user.id, similarity_threshold=-1.0)
    assert len(results) == 1


def test_session_lifecycle_through_manager(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)
    session_id = str(uuid.uuid4())

    manager.session.remember(session_id, user.id, "last_query", "binary trees")
    state = manager.get_session_state(session_id, user.id)
    assert state == {"last_query": "binary trees"}

    manager.end_session(session_id)
    assert manager.get_session_state(session_id, user.id) == {}


def test_delete_history_with_no_filter_removes_everything(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)
    manager.remember(user.id, "one", persist_long_term=False)
    manager.remember(user.id, "two", persist_long_term=True)

    deleted = manager.delete_history(user.id)
    assert deleted == 2
    assert manager.get_history(user.id) == []


def test_delete_history_filtered_by_type_preserves_others(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)
    manager.remember(user.id, "short one", persist_long_term=False)
    manager.remember(user.id, "long one", persist_long_term=True)

    deleted = manager.delete_history(user.id, memory_type=MemoryType.SHORT_TERM)
    assert deleted == 1

    remaining = manager.get_history(user.id)
    assert len(remaining) == 1
    assert remaining[0].memory_type == MemoryType.LONG_TERM


def test_delete_history_long_term_also_removes_vectors(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)
    manager.remember(user.id, "insight to be removed", persist_long_term=True)
    assert manager.long_term.vector_store.ntotal == 1

    manager.delete_history(user.id, memory_type=MemoryType.LONG_TERM)
    assert manager.long_term.vector_store.ntotal == 0


def test_clear_all_removes_every_memory_type(db_session) -> None:
    user = _make_user(db_session)
    manager = MemoryManager(db_session)
    manager.remember(user.id, "short one", persist_long_term=False)
    manager.remember(user.id, "long one", persist_long_term=True)

    cleared = manager.clear_all(user.id)
    assert cleared == 2
    assert manager.get_history(user.id) == []
    assert manager.long_term.vector_store.ntotal == 0


def test_working_memory_is_isolated_per_manager_instance(db_session) -> None:
    """Confirms MemoryManager respects the injected WorkingMemoryService — see its docstring."""
    from services.working_memory_service import WorkingMemoryService

    wm1 = WorkingMemoryService()
    wm1.remember("k", "v1")
    manager1 = MemoryManager(db_session, working_memory=wm1)
    assert manager1.working.recall("k") == "v1"

    wm2 = WorkingMemoryService()
    manager2 = MemoryManager(db_session, working_memory=wm2)
    assert manager2.working.recall("k") is None
