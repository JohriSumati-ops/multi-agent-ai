"""
services/working_memory_service.py — Phase 4

WHY THIS FILE EXISTS
---------------------
`memory/working_memory.py::WorkingMemory` is the storage primitive; this
service is what `api/deps.py` actually injects into routes, following the
exact same "service wraps a primitive, constructed fresh per request via
Depends()" shape as every other service in this project. There is
deliberately very little logic here — working memory's whole point is
that it stays simple and disappears automatically (see
memory/working_memory.py's docstring).
"""

from __future__ import annotations

from typing import Any

from memory.working_memory import WorkingMemory


class WorkingMemoryService:
    """
    Constructed fresh per request (see api/deps.py::get_working_memory_service)
    — never cached, never a singleton. Automatically discarded when the
    request completes, which is the entirety of its "automatic clearing"
    guarantee; no explicit lifecycle hook is needed for that to hold.
    """

    def __init__(self) -> None:
        self._store = WorkingMemory()

    def remember(self, key: str, value: Any) -> None:
        self._store.set(key, value)

    def recall(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def forget(self, key: str) -> None:
        self._store.delete(key)

    def clear(self) -> None:
        self._store.clear()

    def snapshot(self) -> dict[str, Any]:
        return self._store.as_dict()

    def __len__(self) -> int:
        return len(self._store)
