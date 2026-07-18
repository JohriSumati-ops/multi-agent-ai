"""
agents/activity_timeline.py — AGENT ACTIVITY TIMELINE

WHY THIS FILE EXISTS
---------------------
Phase 1 requirement: the frontend needs to eventually render a step-by-step
timeline of which agents ran for a given request (Supervisor → Retriever →
Memory → Reader → Recommendation, per Architecture Section 4.4's
AgentActivityIndicator). That data already has a persistence home
(`AgentExecutionLog`, ordered by `step_order` within a `task_id`) — this
module is the read-side helper that turns a set of log rows into the
ordered structure the API/frontend actually wants.

No agents exist yet, so this module cannot be exercised end-to-end in
Phase 1, but its shape is fixed now so the future `GET
/conversations/{id}/timeline` endpoint has an obvious implementation to
call.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Read-model / view construction kept separate from the write-side log
(`AgentExecutionLog`) — the stored rows are optimized for insertion (one
row per agent step, written as it happens); this module reshapes them into
the nested, ordered structure a UI timeline actually consumes. Keeping that
transformation in one function avoids duplicating "how do I turn log rows
into a timeline" logic in multiple routes.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
`services/` will call `build_timeline(logs)` after fetching all
`AgentExecutionLog` rows for a `task_id` via
`AgentExecutionLogRepository.get_by_task_id`, then return the result to the
frontend as part of a chat response.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TimelineStep:
    agent_name: str
    status: str
    step_order: int
    latency_ms: int | None
    confidence_score: float | None


def build_timeline(log_rows: list) -> list[TimelineStep]:
    """
    Convert a list of AgentExecutionLog ORM rows (all sharing one task_id)
    into an ordered timeline the frontend can render directly.

    `log_rows` is typed loosely (not `list[AgentExecutionLog]`) to avoid
    this module depending on the ORM layer — it only needs objects with the
    listed attributes, which keeps it testable with plain stub objects.
    """
    ordered = sorted(log_rows, key=lambda row: row.step_order)
    return [
        TimelineStep(
            agent_name=row.agent_name,
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            step_order=row.step_order,
            latency_ms=row.latency_ms,
            confidence_score=row.confidence_score,
        )
        for row in ordered
    ]
