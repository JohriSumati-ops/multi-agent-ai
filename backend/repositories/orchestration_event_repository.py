"""
repositories/orchestration_event_repository.py — Phase 5
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.orchestration_event import OrchestrationEvent
from repositories.base_repository import BaseRepository


class OrchestrationEventRepository(BaseRepository[OrchestrationEvent]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, OrchestrationEvent)

    def list_for_plan(self, plan_id: str) -> list[OrchestrationEvent]:
        stmt = (
            select(OrchestrationEvent)
            .where(OrchestrationEvent.plan_id == plan_id)
            .order_by(OrchestrationEvent.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_for_task(self, task_id: str) -> list[OrchestrationEvent]:
        stmt = (
            select(OrchestrationEvent)
            .where(OrchestrationEvent.task_id == task_id)
            .order_by(OrchestrationEvent.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
