"""
tests/test_memory_search_service.py
"""

from __future__ import annotations

import uuid

from models.memory_access_log import MemoryAccessType
from models.user import User
from services.long_term_memory_service import LongTermMemoryService
from services.memory_search_service import MemorySearchService


def _make_user(db_session, email="msearch@example.com") -> User:
    user = User(email=email, hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_search_finds_relevant_long_term_memory(db_session) -> None:
    user = _make_user(db_session)
    LongTermMemoryService(db_session).write(user.id, "User struggles with recursion base cases")
    LongTermMemoryService(db_session).write(user.id, "User prefers visual explanations")

    results = MemorySearchService(db_session).search(query="recursion base cases", user_id=user.id, similarity_threshold=-1.0)
    assert len(results) == 2  # fake backend has no real semantic signal, but both should be returned/ranked
    assert results[0].reason  # explainability present


def test_search_returns_empty_for_user_with_no_memory(db_session) -> None:
    user = _make_user(db_session)
    results = MemorySearchService(db_session).search(query="anything", user_id=user.id)
    assert results == []


def test_search_excludes_other_users_memory(db_session) -> None:
    user_a = _make_user(db_session, "a@example.com")
    user_b = _make_user(db_session, "b@example.com")
    LongTermMemoryService(db_session).write(user_a.id, "user A's private insight")

    results = MemorySearchService(db_session).search(query="private insight", user_id=user_b.id, similarity_threshold=-1.0)
    assert results == []


def test_search_logs_access_for_each_result(db_session) -> None:
    user = _make_user(db_session)
    memory = LongTermMemoryService(db_session).write(user.id, "a memorable insight")

    service = MemorySearchService(db_session)
    service.search(query="insight", user_id=user.id, similarity_threshold=-1.0)

    accesses = service.access_log_repo.count_accesses_for_user(user.id)
    assert accesses == 1


def test_find_similar_to_memory_excludes_itself(db_session) -> None:
    user = _make_user(db_session)
    ltm = LongTermMemoryService(db_session)
    memory_a = ltm.write(user.id, "insight about trees")
    ltm.write(user.id, "insight about graphs")

    service = MemorySearchService(db_session)
    results = service.find_similar_to_memory(memory_id=memory_a.id, user_id=user.id, similarity_threshold=-1.0)
    assert all(r.chunk_id != str(memory_a.id) for r in results)


def test_find_similar_to_memory_raises_for_other_users_memory(db_session) -> None:
    from core.exceptions import MemoryNotFoundError

    user_a = _make_user(db_session, "a2@example.com")
    user_b = _make_user(db_session, "b2@example.com")
    memory = LongTermMemoryService(db_session).write(user_a.id, "user A's memory")

    service = MemorySearchService(db_session)
    try:
        service.find_similar_to_memory(memory_id=memory.id, user_id=user_b.id)
        assert False, "expected MemoryNotFoundError"
    except MemoryNotFoundError:
        pass
