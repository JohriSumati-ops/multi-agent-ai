"""
api/routes/orchestration.py — Phase 5

WHY THIS FILE EXISTS
---------------------
The HTTP surface for the Intelligence Layer. Per the "routers are
transport-only" rule established in Phase 1, every handler here does
nothing but read the request, call `OrchestrationService`, and shape the
response. `POST /orchestration/execute` is intentionally goal +
capability-driven (not free-text intent parsing) — see docs/Phase5.md
Section 4 for why: this phase has no LLM to parse free text into an
intent, so the client (or, in a future phase, an LLM-based intent
classifier sitting in front of this exact endpoint) specifies the
capabilities directly.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import CurrentUser, OrchestrationServiceDep
from schemas.base import APIResponse
from schemas.orchestration import (
    CapabilityOut,
    DecisionTraceOut,
    ExecuteGoalRequest,
    ExecuteGoalResponse,
    ExecutionPlanOut,
    HealthCheckOut,
    TaskTimelineEntryOut,
)

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


@router.post("/execute", response_model=APIResponse[ExecuteGoalResponse])
def execute_goal(
    payload: ExecuteGoalRequest, service: OrchestrationServiceDep, user: CurrentUser
) -> APIResponse[ExecuteGoalResponse]:
    result = service.run_goal(
        goal=payload.goal,
        capabilities=payload.capabilities,
        payload=payload.payload,
        user_id=user.id,
        request_text=payload.request_text,
    )

    plan_out = ExecutionPlanOut(
        plan_id=result.plan.id,
        goal=result.plan.goal,
        task_count=len(result.plan.tasks),
        succeeded=len(result.plan.successful_tasks()),
        failed=len(result.plan.failed_tasks()),
    )
    trace_out = DecisionTraceOut(
        plan_id=result.trace.plan_id,
        goal=result.trace.goal,
        timeline=[TaskTimelineEntryOut(**vars(entry)) for entry in result.trace.timeline],
        agent_selection_reasons=result.trace.agent_selection_reasons,
        agents_not_selected=result.trace.agents_not_selected,
        context_sources=result.trace.context_sources,
        overall_reason=result.trace.explanation.reason if result.trace.explanation else "",
        overall_confidence=result.trace.explanation.confidence if result.trace.explanation else None,
    )

    return APIResponse[ExecuteGoalResponse](success=True, data=ExecuteGoalResponse(plan=plan_out, trace=trace_out))


@router.get("/capabilities", response_model=APIResponse[list[CapabilityOut]])
def list_capabilities(service: OrchestrationServiceDep, user: CurrentUser) -> APIResponse[list[CapabilityOut]]:
    capabilities = service.list_capabilities()
    return APIResponse[list[CapabilityOut]](success=True, data=[CapabilityOut(**c) for c in capabilities])


@router.get("/health", response_model=APIResponse[list[HealthCheckOut]])
def health_check(service: OrchestrationServiceDep, user: CurrentUser) -> APIResponse[list[HealthCheckOut]]:
    results = service.health_check()
    return APIResponse[list[HealthCheckOut]](success=True, data=[HealthCheckOut(**r) for r in results])
