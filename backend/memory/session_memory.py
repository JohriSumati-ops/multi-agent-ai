"""
memory/session_memory.py — Phase 4

WHY THIS FILE EXISTS
---------------------
See docs/Phase4.md Sections 3.4 and 12 for the full design rationale.
Unlike `WorkingMemory` (deliberately not a singleton), session memory must
survive across multiple requests within one session, so it follows the
exact singleton pattern `retrieval/embedder.py::EmbeddingService` and
`retrieval/vector_store.py`'s `get_vector_store()` already established:
one process-wide store, a `get_instance()`/`reset_instance()` pair for
test isolation, and a `threading.Lock` guarding mutation.

NO SERVER-SIDE SESSION SYSTEM EXISTS
------------------------------------------
This project's auth (Phase 2) is stateless JWT — there is no login-time
session creation to hook into. `SessionMemory` therefore treats whatever
`session_id` string a caller provides as the key; nothing here validates
that a session "legitimately" exists, just that its data hasn't expired.
`services/session_memory_service.py` is the layer that ties this to a
specific authenticated user.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class _SessionEntry:
    data: dict[str, Any] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SessionMemory:
    """
    Process-wide, thread-safe, TTL-based session store.

    Every read/write updates `last_activity`, so a session only expires
    after `ttl_minutes` of genuine inactivity — not from a fixed clock
    starting at creation.
    """

    def __init__(self, ttl_minutes: int) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict[str, _SessionEntry] = {}
        self._lock = threading.Lock()

    def _is_expired(self, entry: _SessionEntry) -> bool:
        return datetime.now(timezone.utc) - entry.last_activity > self._ttl

    def _touch_and_get(self, session_id: str) -> _SessionEntry | None:
        entry = self._sessions.get(session_id)
        if entry is None:
            return None
        if self._is_expired(entry):
            del self._sessions[session_id]
            return None
        entry.last_activity = datetime.now(timezone.utc)
        return entry

    def set(self, session_id: str, key: str, value: Any) -> None:
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None or self._is_expired(entry):
                entry = _SessionEntry()
                self._sessions[session_id] = entry
            entry.data[key] = value
            entry.last_activity = datetime.now(timezone.utc)

    def get(self, session_id: str, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._touch_and_get(session_id)
            if entry is None:
                return default
            return entry.data.get(key, default)

    def get_all(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            entry = self._touch_and_get(session_id)
            return dict(entry.data) if entry else {}

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return self._touch_and_get(session_id) is not None

    def end_session(self, session_id: str) -> bool:
        """Explicitly destroy a session. Returns True if a session existed to destroy."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def prune_expired(self) -> int:
        """Sweep and remove all expired sessions. Returns the number removed."""
        with self._lock:
            expired = [sid for sid, entry in self._sessions.items() if self._is_expired(entry)]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)

    def active_session_count(self) -> int:
        with self._lock:
            return sum(1 for entry in self._sessions.values() if not self._is_expired(entry))


# --------------------------------------------------------------------- #
# Process-wide singleton, mirroring EmbeddingService/get_vector_store's pattern.
# --------------------------------------------------------------------- #
_instance: SessionMemory | None = None
_instance_lock = threading.Lock()


def get_session_memory(ttl_minutes: int | None = None) -> SessionMemory:
    global _instance
    if _instance is not None:
        return _instance
    with _instance_lock:
        if _instance is None:
            from core.config import settings

            _instance = SessionMemory(ttl_minutes or settings.SESSION_MEMORY_TTL_MINUTES)
    return _instance


def reset_session_memory() -> None:
    """Test-only: clears the singleton so the next get_session_memory() rebuilds it."""
    global _instance
    with _instance_lock:
        _instance = None
