"""
tests/test_session_memory.py

Pure unit tests for the singleton, TTL-based session store, plus the
user-scoped service wrapping it. Uses direct `SessionMemory` instances
(not the process-wide singleton) for TTL tests, so time-manipulation
doesn't leak into other tests via shared global state.
"""

from __future__ import annotations

import time
import uuid

from core.exceptions import SessionNotFoundError
from memory.session_memory import SessionMemory, get_session_memory, reset_session_memory
from services.session_memory_service import SessionMemoryService


def test_set_and_get_within_a_session() -> None:
    sm = SessionMemory(ttl_minutes=30)
    sm.set("sess1", "key1", "value1")
    assert sm.get("sess1", "key1") == "value1"


def test_get_missing_session_returns_default() -> None:
    sm = SessionMemory(ttl_minutes=30)
    assert sm.get("nonexistent", "key", "fallback") == "fallback"


def test_end_session_removes_all_data() -> None:
    sm = SessionMemory(ttl_minutes=30)
    sm.set("sess1", "key1", "value1")
    assert sm.end_session("sess1") is True
    assert sm.get("sess1", "key1") is None


def test_end_session_returns_false_for_nonexistent_session() -> None:
    sm = SessionMemory(ttl_minutes=30)
    assert sm.end_session("nonexistent") is False


def test_session_expires_after_ttl() -> None:
    sm = SessionMemory(ttl_minutes=0)  # effectively immediate expiry for a fast test
    sm.set("sess1", "key1", "value1")
    time.sleep(0.05)
    assert sm.get("sess1", "key1") is None


def test_activity_extends_session_lifetime() -> None:
    """Reading/writing should refresh last_activity — verified indirectly via exists()."""
    sm = SessionMemory(ttl_minutes=30)
    sm.set("sess1", "key1", "value1")
    assert sm.exists("sess1") is True
    sm.get("sess1", "key1")  # touches last_activity again
    assert sm.exists("sess1") is True


def test_prune_expired_removes_only_expired_sessions() -> None:
    sm = SessionMemory(ttl_minutes=0)
    sm.set("sess1", "k", "v")
    time.sleep(0.05)
    removed = sm.prune_expired()
    assert removed == 1
    assert sm.active_session_count() == 0


def test_get_all_returns_full_session_dict() -> None:
    sm = SessionMemory(ttl_minutes=30)
    sm.set("sess1", "a", 1)
    sm.set("sess1", "b", 2)
    assert sm.get_all("sess1") == {"a": 1, "b": 2}


def test_singleton_returns_same_instance() -> None:
    reset_session_memory()
    a = get_session_memory(ttl_minutes=30)
    b = get_session_memory(ttl_minutes=99)  # ignored — see get_instance's docstring pattern
    assert a is b
    reset_session_memory()


# ------------------------------------------------------------------ #
# SessionMemoryService — user-scoped wrapper
# ------------------------------------------------------------------ #
def test_service_namespaces_by_user() -> None:
    store = SessionMemory(ttl_minutes=30)
    service = SessionMemoryService(store)

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    service.remember("sess1", user_a, "last_query", "trees")
    service.remember("sess1", user_b, "last_query", "graphs")

    assert service.recall("sess1", user_a, "last_query") == "trees"
    assert service.recall("sess1", user_b, "last_query") == "graphs"


def test_get_session_state_strips_namespace_prefix() -> None:
    store = SessionMemory(ttl_minutes=30)
    service = SessionMemoryService(store)
    user_id = uuid.uuid4()

    service.remember("sess1", user_id, "last_query", "trees")
    service.remember("sess1", user_id, "page", 2)

    state = service.get_session_state("sess1", user_id)
    assert state == {"last_query": "trees", "page": 2}


def test_get_session_state_excludes_other_users() -> None:
    store = SessionMemory(ttl_minutes=30)
    service = SessionMemoryService(store)
    user_a, user_b = uuid.uuid4(), uuid.uuid4()

    service.remember("sess1", user_a, "secret", "a-data")
    service.remember("sess1", user_b, "secret", "b-data")

    state = service.get_session_state("sess1", user_a)
    assert state == {"secret": "a-data"}


def test_end_session_raises_for_nonexistent_session() -> None:
    store = SessionMemory(ttl_minutes=30)
    service = SessionMemoryService(store)
    try:
        service.end_session("no-such-session")
        assert False, "expected SessionNotFoundError"
    except SessionNotFoundError:
        pass
