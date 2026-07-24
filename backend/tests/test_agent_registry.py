"""
tests/test_agent_registry.py
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from orchestration.agent_registry import (
    AgentRegistry,
    CapabilityNotRegisteredError,
    get_agent_registry,
)


class _DummyAgent(BaseAgent):
    name = "dummy_agent"

    def execute(self, context):
        return "dummy result"


def test_register_and_get() -> None:
    registry = AgentRegistry()
    registry.register("dummy", _DummyAgent)
    registration = registry.get("dummy")
    assert registration.agent_class is _DummyAgent


def test_get_raises_for_unregistered_capability() -> None:
    registry = AgentRegistry()
    try:
        registry.get("nonexistent")
        assert False, "expected CapabilityNotRegisteredError"
    except CapabilityNotRegisteredError:
        pass


def test_try_get_returns_none_for_unregistered_capability() -> None:
    registry = AgentRegistry()
    assert registry.try_get("nonexistent") is None


def test_unregister_removes_capability() -> None:
    registry = AgentRegistry()
    registry.register("dummy", _DummyAgent)
    assert registry.unregister("dummy") is True
    assert registry.is_registered("dummy") is False


def test_unregister_returns_false_for_unknown_capability() -> None:
    registry = AgentRegistry()
    assert registry.unregister("nonexistent") is False


def test_re_registering_a_capability_replaces_the_agent_class() -> None:
    class _AnotherAgent(BaseAgent):
        name = "another"

        def execute(self, context):
            return "another result"

    registry = AgentRegistry()
    registry.register("dummy", _DummyAgent)
    registry.register("dummy", _AnotherAgent)
    assert registry.get("dummy").agent_class is _AnotherAgent


def test_list_returns_all_registrations() -> None:
    registry = AgentRegistry()
    registry.register("a", _DummyAgent)
    registry.register("b", _DummyAgent)
    assert len(registry.list()) == 2


def test_capabilities_returns_sorted_names() -> None:
    registry = AgentRegistry()
    registry.register("zebra", _DummyAgent)
    registry.register("alpha", _DummyAgent)
    assert registry.capabilities() == ["alpha", "zebra"]


def test_health_with_no_health_check_defined_assumes_healthy() -> None:
    registry = AgentRegistry()
    registry.register("dummy", _DummyAgent)
    results = registry.health()
    assert len(results) == 1
    assert results[0].healthy is True


def test_health_uses_custom_health_check_when_defined() -> None:
    class _UnhealthyAgent(BaseAgent):
        name = "unhealthy"

        @staticmethod
        def is_healthy():
            return False, "model not loaded"

        def execute(self, context):
            return None

    registry = AgentRegistry()
    registry.register("unhealthy_capability", _UnhealthyAgent)
    results = registry.health("unhealthy_capability")
    assert results[0].healthy is False
    assert "model not loaded" in results[0].detail


def test_health_check_that_raises_is_treated_as_unhealthy() -> None:
    class _BrokenHealthCheckAgent(BaseAgent):
        name = "broken"

        @staticmethod
        def is_healthy():
            raise RuntimeError("boom")

        def execute(self, context):
            return None

    registry = AgentRegistry()
    registry.register("broken_capability", _BrokenHealthCheckAgent)
    results = registry.health("broken_capability")
    assert results[0].healthy is False
    assert "boom" in results[0].detail


def test_clear_removes_all_registrations() -> None:
    registry = AgentRegistry()
    registry.register("a", _DummyAgent)
    registry.clear()
    assert registry.capabilities() == []


def test_default_registry_includes_the_three_existing_agents() -> None:
    registry = get_agent_registry()
    assert set(registry.capabilities()) == {"parse_document", "extract_metadata", "generate_embeddings"}


def test_default_registry_declares_extract_metadata_depends_on_parse_document() -> None:
    registry = get_agent_registry()
    registration = registry.get("extract_metadata")
    assert "parse_document" in registration.depends_on_capabilities
