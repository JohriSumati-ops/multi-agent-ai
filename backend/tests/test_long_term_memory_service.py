"""
tests/test_long_term_memory_service.py
"""

from __future__ import annotations

from models.memory import MemoryType
from models.user import User
from services.long_term_memory_service import LongTermMemoryService


def _make_user(db_session) -> User:
    user = User(email="ltm@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_write_creates_long_term_memory_without_expiry(db_session) -> None:
    user = _make_user(db_session)
    service = LongTermMemoryService(db_session)

    memory = service.write(user.id, "User struggles with recursion base cases", importance_score=0.9)
    assert memory.memory_type == MemoryType.LONG_TERM
    assert memory.expires_at is None
    assert memory.importance_score == 0.9


def test_write_indexes_memory_for_semantic_search(db_session) -> None:
    user = _make_user(db_session)
    service = LongTermMemoryService(db_session)

    memory = service.write(user.id, "User struggles with recursion base cases")
    embedding = service.embedding_repo.get_by_memory_id(memory.id)
    assert embedding is not None
    assert embedding.dimension == service.embedding_service.dimension
    assert service.vector_store.ntotal == 1


def test_read_returns_long_term_memories(db_session) -> None:
    user = _make_user(db_session)
    service = LongTermMemoryService(db_session)
    service.write(user.id, "insight one")
    service.write(user.id, "insight two")

    results = service.read(user.id)
    assert len(results) == 2


def test_update_content_reindexes_the_memory(db_session) -> None:
    user = _make_user(db_session)
    service = LongTermMemoryService(db_session)
    memory = service.write(user.id, "original content")

    old_embedding = service.embedding_repo.get_by_memory_id(memory.id)
    updated = service.update(memory.id, content="updated content")

    assert updated.content == "updated content"
    new_embedding = service.embedding_repo.get_by_memory_id(memory.id)
    assert new_embedding is not None
    # Vector count should stay at 1 — old vector removed, new one added, not both kept.
    assert service.vector_store.ntotal == 1
    assert new_embedding.vector_id == old_embedding.vector_id  # same chunk_uuid_to_vector_id derivation


def test_update_importance_only_does_not_reindex(db_session) -> None:
    user = _make_user(db_session)
    service = LongTermMemoryService(db_session)
    memory = service.write(user.id, "stable content")

    updated = service.update(memory.id, importance_score=0.95)
    assert updated.importance_score == 0.95
    assert updated.content == "stable content"


def test_delete_removes_memory_and_its_vector(db_session) -> None:
    user = _make_user(db_session)
    service = LongTermMemoryService(db_session)
    memory = service.write(user.id, "to be deleted")
    assert service.vector_store.ntotal == 1

    service.delete(memory.id)
    assert service.repo.get(memory.id) is None
    assert service.embedding_repo.get_by_memory_id(memory.id) is None
    assert service.vector_store.ntotal == 0


def test_update_raises_for_nonexistent_memory(db_session) -> None:
    import uuid

    from core.exceptions import MemoryNotFoundError

    service = LongTermMemoryService(db_session)
    try:
        service.update(uuid.uuid4(), content="x")
        assert False, "expected MemoryNotFoundError"
    except MemoryNotFoundError:
        pass
