"""
tests/test_working_memory.py

Pure unit tests — no database, no singleton, no network. Verifies working
memory's core property: it's a plain, isolated, per-instance store.
"""

from __future__ import annotations

from memory.working_memory import WorkingMemory
from services.working_memory_service import WorkingMemoryService


def test_working_memory_set_and_get() -> None:
    wm = WorkingMemory()
    wm.set("key1", "value1")
    assert wm.get("key1") == "value1"


def test_working_memory_get_missing_key_returns_default() -> None:
    wm = WorkingMemory()
    assert wm.get("missing", "fallback") == "fallback"


def test_working_memory_has_and_delete() -> None:
    wm = WorkingMemory()
    wm.set("k", "v")
    assert wm.has("k") is True
    wm.delete("k")
    assert wm.has("k") is False


def test_working_memory_clear_empties_store() -> None:
    wm = WorkingMemory()
    wm.set("a", 1)
    wm.set("b", 2)
    wm.clear()
    assert len(wm) == 0


def test_working_memory_as_dict_returns_a_copy() -> None:
    wm = WorkingMemory()
    wm.set("a", 1)
    snapshot = wm.as_dict()
    snapshot["a"] = 999
    assert wm.get("a") == 1  # original store unaffected by mutating the snapshot


def test_two_working_memory_instances_are_fully_isolated() -> None:
    """The core guarantee: no shared state between two 'requests'."""
    wm1 = WorkingMemory()
    wm2 = WorkingMemory()
    wm1.set("shared_key", "from_wm1")
    assert wm2.get("shared_key") is None


def test_working_memory_service_wraps_store_correctly() -> None:
    service = WorkingMemoryService()
    service.remember("query", "binary trees")
    assert service.recall("query") == "binary trees"
    assert len(service) == 1
    service.forget("query")
    assert service.recall("query") is None


def test_working_memory_service_instances_are_isolated() -> None:
    """Simulates two different requests each getting their own service instance."""
    service_a = WorkingMemoryService()
    service_b = WorkingMemoryService()
    service_a.remember("x", 1)
    assert service_b.recall("x") is None


def test_working_memory_service_snapshot() -> None:
    service = WorkingMemoryService()
    service.remember("a", 1)
    service.remember("b", 2)
    assert service.snapshot() == {"a": 1, "b": 2}
