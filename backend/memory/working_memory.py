"""
memory/working_memory.py — Phase 4

WHY THIS FILE EXISTS
---------------------
See docs/Phase4.md Section 3.1. Working memory's entire correctness
property — "gone after one request" — comes from HOW this class is
instantiated, not from any special clearing logic inside it: it is
deliberately NOT a singleton (contrast with `SessionMemoryStore` below, and
with `retrieval/embedder.py::EmbeddingService`). `services/working_memory_service.py`
constructs a fresh `WorkingMemory` per request via FastAPI's `Depends()`,
exactly like `DocumentService`/`SemanticSearchService` already do — once
the request finishes, nothing references the instance anymore and Python
garbage-collects it. No explicit "clear" call is needed for this to be
true, though `clear()` is provided for callers that want to reuse one
instance across multiple logical steps within the same request.

RELATIONSHIP TO core/agent_bus.py::TaskContext
---------------------------------------------------
`TaskContext` (Phase 1) is, in every meaningful sense, already a
working-memory object scoped to one agent pipeline run. This class doesn't
replace it — it generalizes the same "ephemeral, per-request scratch
space" pattern into a small reusable utility any service can use, not just
the agent pipeline specifically.
"""

from __future__ import annotations

from typing import Any


class WorkingMemory:
    """A plain, in-process key-value scratch space for the lifetime of one request."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._store

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def as_dict(self) -> dict[str, Any]:
        """Snapshot for debugging/logging — returns a copy, not the live store."""
        return dict(self._store)

    def __len__(self) -> int:
        return len(self._store)
