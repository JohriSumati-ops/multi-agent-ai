"""
tests/test_short_term_memory_service.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.config import settings
from models.memory import MemoryType
from models.user import User
from services.short_term_memory_service import ShortTermMemoryService


def _make_user(db_session) -> User:
    user = User(email="stm@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes for TIMESTAMP(timezone=True) columns — see
    services/memory_cleanup_service.py's identical helper for the full explanation."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def test_write_creates_short_term_memory_with_expiry(db_session) -> None:
    user = _make_user(db_session)
    service = ShortTermMemoryService(db_session)

    memory = service.write(user.id, "Searched for binary trees")
    assert memory.memory_type == MemoryType.SHORT_TERM
    assert memory.expires_at is not None
    assert _as_utc(memory.expires_at) > datetime.now(timezone.utc)


def test_read_returns_active_memories_only(db_session) -> None:
    user = _make_user(db_session)
    service = ShortTermMemoryService(db_session)

    service.write(user.id, "recent search 1")
    service.write(user.id, "recent search 2")

    results = service.read(user.id)
    assert len(results) == 2


def test_record_conversation_turn_scopes_to_conversation(db_session) -> None:
    import uuid

    user = _make_user(db_session)
    service = ShortTermMemoryService(db_session)
    conversation_id = uuid.uuid4()

    memory = service.record_conversation_turn(user.id, conversation_id, "Explained trees")
    assert memory.conversation_id == conversation_id


def test_record_upload_scopes_to_document(db_session) -> None:
    import uuid

    user = _make_user(db_session)
    service = ShortTermMemoryService(db_session)
    document_id = uuid.uuid4()

    memory = service.record_upload(user.id, document_id, "Trees Notes")
    assert memory.document_id == document_id
    assert "Trees Notes" in memory.content


def test_record_search_and_retrieval_produce_readable_content(db_session) -> None:
    user = _make_user(db_session)
    service = ShortTermMemoryService(db_session)

    search_memory = service.record_search(user.id, "binary search trees")
    retrieval_memory = service.record_retrieval(user.id, "binary search trees", 3)

    assert "binary search trees" in search_memory.content
    assert "3" in retrieval_memory.content


def test_size_cap_enforcement_keeps_only_the_given_count(db_session, monkeypatch) -> None:
    """
    Verifies the cap itself is enforced (count reduced to the limit).
    Does NOT assert *which* specific items survive — see
    test_size_cap_enforcement_keeps_newest_by_explicit_timestamp below for
    that, since SQLite's 1-second timestamp resolution makes rapid
    successive writes in a tight loop share an identical `created_at`,
    which was discovered while first writing this test (see
    repositories/memory_repository.py::delete_excess_for_type's docstring).
    """
    monkeypatch.setattr(settings, "SHORT_TERM_MEMORY_MAX_ITEMS", 3)
    user = _make_user(db_session)
    service = ShortTermMemoryService(db_session)

    for i in range(5):
        service.write(user.id, f"memory number {i}")

    results = service.read(user.id, limit=100)
    assert len(results) == 3


def test_size_cap_enforcement_keeps_newest_by_explicit_timestamp(db_session, monkeypatch) -> None:
    """
    Same scenario as above, but with `created_at` set explicitly (bypassing
    the database's real-time clock entirely) so "newest survives" is
    unambiguous and independent of any database's timestamp resolution.
    """
    user = _make_user(db_session)
    service = ShortTermMemoryService(db_session)

    # Temporarily disable the cap so all 5 writes survive the loop —
    # otherwise write()'s own internal enforcement would delete rows
    # before we get a chance to assign them explicit timestamps below.
    monkeypatch.setattr(settings, "SHORT_TERM_MEMORY_MAX_ITEMS", 100)
    written = [service.write(user.id, f"memory number {i}") for i in range(5)]

    base_time = datetime.now(timezone.utc)
    for i, memory in enumerate(written):
        memory.created_at = base_time + timedelta(seconds=i)
        service.repo.commit_refresh(memory)

    monkeypatch.setattr(settings, "SHORT_TERM_MEMORY_MAX_ITEMS", 3)
    service._enforce_size_cap(user.id)

    results = service.read(user.id, limit=100)
    contents = {m.content for m in results}
    assert len(results) == 3
    assert contents == {"memory number 2", "memory number 3", "memory number 4"}
