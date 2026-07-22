"""
services/session_memory_service.py — Phase 4

WHY THIS FILE EXISTS
---------------------
Thin service layer over `memory/session_memory.py::SessionMemory`,
namespacing every key by `(session_id, user_id)` conceptually — in
practice, by requiring the caller to always pass both, so one user can
never read or overwrite another user's session data even if two session
IDs were to collide (a client-generated UUID collision is astronomically
unlikely, but scoping by user costs nothing and removes the concern
entirely).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from core.exceptions import SessionNotFoundError
from memory.session_memory import SessionMemory, get_session_memory


class SessionMemoryService:
    def __init__(self, store: SessionMemory | None = None) -> None:
        self.store = store or get_session_memory()

    @staticmethod
    def _namespaced_key(user_id: UUID, key: str) -> str:
        return f"{user_id}:{key}"

    def remember(self, session_id: str, user_id: UUID, key: str, value: Any) -> None:
        self.store.set(session_id, self._namespaced_key(user_id, key), value)

    def recall(self, session_id: str, user_id: UUID, key: str, default: Any = None) -> Any:
        return self.store.get(session_id, self._namespaced_key(user_id, key), default)

    def get_session_state(self, session_id: str, user_id: UUID) -> dict[str, Any]:
        """Returns only this user's keys within the session, stripped of the namespace prefix."""
        prefix = f"{user_id}:"
        all_data = self.store.get_all(session_id)
        return {k.removeprefix(prefix): v for k, v in all_data.items() if k.startswith(prefix)}

    def end_session(self, session_id: str) -> None:
        if not self.store.end_session(session_id):
            raise SessionNotFoundError(f"No active session found for session_id={session_id}")

    def session_exists(self, session_id: str) -> bool:
        return self.store.exists(session_id)
