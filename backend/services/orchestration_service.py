"""
services/orchestration_service.py — Phase 5

WHY THIS FILE EXISTS
---------------------
`api/routes/orchestration.py` needs a service to depend on, following the
exact same pattern every previous phase's API layer used
(`DocumentService`, `SemanticSearchService`, `MemoryManager`). This class
is thin by design: it constructs a `ContextBuilder` from the existing
memory/retrieval services, constructs a `SupervisorAgent`, and wraps the
`TaskContext` plumbing `agents/supervisor_agent.py` expects — no
orchestration logic of its own lives here.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from agents.supervisor_agent import SupervisorAgent, SupervisorResult
from core.agent_bus import TaskContext
from orchestration.agent_registry import get_agent_registry
from orchestration.context_builder import ContextBuilder
from services.memory_manager import MemoryManager
from services.semantic_search_service import SemanticSearchService
from services.working_memory_service import WorkingMemoryService


class OrchestrationService:
    def __init__(self, db: Session, *, working_memory: WorkingMemoryService | None = None) -> None:
        self.db = db
        self.registry = get_agent_registry()
        self.working_memory = working_memory or WorkingMemoryService()
        self.memory_manager = MemoryManager(db, working_memory=self.working_memory)
        self.search_service = SemanticSearchService(db)
        self.context_builder = ContextBuilder(
            working_memory=self.working_memory,
            memory_manager=self.memory_manager,
            search_service=self.search_service,
        )

    def run_goal(
        self,
        *,
        goal: str,
        capabilities: list[str],
        payload: dict | None = None,
        user_id: UUID | None = None,
        request_text: str | None = None,
    ) -> SupervisorResult:
        context = TaskContext(original_query=request_text or "", user_id=str(user_id) if user_id else None)
        context.intermediate_results["goal"] = goal
        context.intermediate_results["capabilities"] = capabilities
        context.intermediate_results["payload"] = payload or {}
        context.intermediate_results["user_id"] = user_id
        context.intermediate_results["request_text"] = request_text
        context.intermediate_results["context_builder"] = self.context_builder
        context.intermediate_results["db"] = self.db

        agent_result = SupervisorAgent(self.registry).run(context)
        if not agent_result.success:
            from core.exceptions import AppException

            error = AppException(agent_result.error_message or "Supervisor execution failed")
            error.status_code = agent_result.error_status_code or 500
            error.error_code = agent_result.error_code or "supervisor_execution_error"
            raise error

        return agent_result.output

    def list_capabilities(self) -> list[dict]:
        return [
            {
                "capability": r.capability,
                "agent_name": r.agent_class.__name__,
                "depends_on": r.depends_on_capabilities,
                "description": r.description,
            }
            for r in self.registry.list()
        ]

    def health_check(self) -> list[dict]:
        return [{"capability": h.capability, "healthy": h.healthy, "detail": h.detail} for h in self.registry.health()]
