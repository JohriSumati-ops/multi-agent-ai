"""
schemas/orchestration.py — Phase 5

Request/response contracts for the orchestration API. Every ID field is
typed `UUID`, not `str` — per docs/Phase4.md Section 11's explicit callout
of Phase 2's `owner_id: str` bug, still the standing rule for every new
schema this project adds.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ExecuteGoalRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=500)
    capabilities: list[str] = Field(min_length=1)
    payload: dict = Field(default_factory=dict)
    request_text: str | None = None


class TaskTimelineEntryOut(BaseModel):
    task_id: str
    capability: str
    agent_name: str | None
    status: str
    started_at: str | None
    completed_at: str | None
    duration_ms: int | None
    confidence: float | None


class ExecutionPlanOut(BaseModel):
    plan_id: str
    goal: str
    task_count: int
    succeeded: int
    failed: int


class DecisionTraceOut(BaseModel):
    plan_id: str
    goal: str
    timeline: list[TaskTimelineEntryOut]
    agent_selection_reasons: dict[str, str]
    agents_not_selected: dict[str, str]
    context_sources: dict[str, int]
    overall_reason: str
    overall_confidence: float | None


class ExecuteGoalResponse(BaseModel):
    plan: ExecutionPlanOut
    trace: DecisionTraceOut


class CapabilityOut(BaseModel):
    capability: str
    agent_name: str
    depends_on: list[str]
    description: str


class HealthCheckOut(BaseModel):
    capability: str
    healthy: bool
    detail: str
