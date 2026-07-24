"""
orchestration/agent_registry.py — THE AGENT REGISTRY

WHY THIS FILE EXISTS
---------------------
Per this phase's explicit requirement: "The Supervisor must never
instantiate agents directly." Without a registry, the Supervisor would
need to import and construct `PDFParsingAgent`, `MetadataExtractionAgent`,
etc. by name — coupling it to every concrete agent class that exists. The
registry inverts that: agents are registered under a `capability` string
at startup, and the Supervisor/PlanBuilder only ever ask "who provides
capability X," never naming a concrete class.

SINGLETON, LIKE EmbeddingService / FAISSVectorStore / SessionMemory
-------------------------------------------------------------------------
Agents are stateless workers (a fresh `BaseAgent` subclass instance is
cheap to construct — see agents/base_agent.py, no expensive model loading
happens in `__init__` for the three agents that exist so far), so unlike
`WorkingMemory` this registry benefits from being a process-wide singleton
built once rather than reconstructed per request — the same reasoning
`retrieval/embedder.py::EmbeddingService` and
`retrieval/vector_store.py::get_vector_store()` already established.

HEALTH CHECKS
----------------
`health()` exists because a registered agent can be *present* but not
*currently usable* — e.g., `EmbeddingAgent` depends on
`EmbeddingService.get_instance()`, and if that singleton hasn't been
initialized yet, the agent would fail on first use. `health()` gives the
Supervisor/PlanBuilder a way to check "is this capability actually
available right now" before committing to a plan that depends on it.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from agents.base_agent import BaseAgent
from core.exceptions import AppException
from core.logging import get_logger

logger = get_logger("agent")


class CapabilityNotRegisteredError(AppException):
    status_code = 404
    error_code = "capability_not_registered"


@dataclass
class AgentRegistration:
    capability: str
    agent_class: type[BaseAgent]
    depends_on_capabilities: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class HealthCheckResult:
    capability: str
    healthy: bool
    detail: str = ""


class AgentRegistry:
    """
    Maps capability strings to agent classes. One capability maps to
    exactly one agent class at a time (re-registering the same capability
    replaces the previous registration — this is deliberate: it's how a
    future phase would swap in an improved agent for an existing
    capability without touching the Supervisor).
    """

    def __init__(self) -> None:
        self._registrations: dict[str, AgentRegistration] = {}
        self._lock = threading.Lock()

    def register(
        self,
        capability: str,
        agent_class: type[BaseAgent],
        *,
        depends_on_capabilities: list[str] | None = None,
        description: str = "",
    ) -> None:
        with self._lock:
            self._registrations[capability] = AgentRegistration(
                capability=capability,
                agent_class=agent_class,
                depends_on_capabilities=depends_on_capabilities or [],
                description=description,
            )
        logger.info("Registered agent %s for capability '%s'", agent_class.__name__, capability)

    def unregister(self, capability: str) -> bool:
        with self._lock:
            existed = self._registrations.pop(capability, None) is not None
        if existed:
            logger.info("Unregistered capability '%s'", capability)
        return existed

    def get(self, capability: str) -> AgentRegistration:
        registration = self._registrations.get(capability)
        if registration is None:
            raise CapabilityNotRegisteredError(f"No agent is registered for capability '{capability}'")
        return registration

    def try_get(self, capability: str) -> AgentRegistration | None:
        return self._registrations.get(capability)

    def list(self) -> list[AgentRegistration]:
        return list(self._registrations.values())

    def capabilities(self) -> list[str]:
        return sorted(self._registrations.keys())

    def is_registered(self, capability: str) -> bool:
        return capability in self._registrations

    def health(self, capability: str | None = None) -> list[HealthCheckResult]:
        """
        Checks whether registered agent(s) are currently usable. A
        `BaseAgent` subclass can optionally expose an `is_healthy()`
        staticmethod/classmethod for a real check (e.g., an agent checking
        whether its underlying model singleton initializes without
        raising); agents that don't define one are assumed healthy simply
        by being registered.
        """
        targets = [self.get(capability)] if capability else self.list()
        results = []
        for registration in targets:
            check = getattr(registration.agent_class, "is_healthy", None)
            if callable(check):
                try:
                    healthy, detail = check()
                except Exception as exc:  # noqa: BLE001 — a broken health check itself means "unhealthy"
                    healthy, detail = False, str(exc)
            else:
                healthy, detail = True, "no health check defined — assumed healthy"
            results.append(HealthCheckResult(capability=registration.capability, healthy=healthy, detail=detail))
        return results

    def clear(self) -> None:
        """Test-only: removes every registration."""
        with self._lock:
            self._registrations.clear()


# --------------------------------------------------------------------- #
# Process-wide singleton — see module docstring for why.
# --------------------------------------------------------------------- #
_instance: AgentRegistry | None = None
_instance_lock = threading.Lock()


def get_agent_registry() -> AgentRegistry:
    global _instance
    if _instance is not None:
        return _instance
    with _instance_lock:
        if _instance is None:
            _instance = AgentRegistry()
            _register_default_agents(_instance)
    return _instance


def _register_default_agents(registry: AgentRegistry) -> None:
    """
    Registers this project's three existing agents (Phase 2/3) under
    stable capability names, so the orchestration layer has real,
    functioning agents to plan against from the moment it's imported —
    without needing a separate bootstrap step that could be forgotten.
    """
    from agents.embedding_agent import EmbeddingAgent
    from agents.metadata_extraction_agent import MetadataExtractionAgent
    from agents.pdf_parsing_agent import PDFParsingAgent

    registry.register(
        "parse_document",
        PDFParsingAgent,
        description="Extracts text/pages from a document file (PDF/TXT/MD/DOCX).",
    )
    registry.register(
        "extract_metadata",
        MetadataExtractionAgent,
        depends_on_capabilities=["parse_document"],
        description="Derives title/author/language/word count from parsed document text.",
    )
    registry.register(
        "generate_embeddings",
        EmbeddingAgent,
        description="Generates vector embeddings for a batch of text chunks.",
    )


def reset_agent_registry() -> None:
    """Test-only: clears the singleton so the next get_agent_registry() rebuilds it with defaults."""
    global _instance
    with _instance_lock:
        _instance = None
