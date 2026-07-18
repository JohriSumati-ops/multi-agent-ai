"""
repositories/agent_execution_log_repository.py

Storage-layer access for agent execution telemetry. `get_by_task_id` is
what `agents/activity_timeline.py`'s `build_timeline` will consume once
agents exist and start writing rows here.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.agent_execution_log import AgentExecutionLog
from repositories.base_repository import BaseRepository


class AgentExecutionLogRepository(BaseRepository[AgentExecutionLog]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AgentExecutionLog)

    def get_by_task_id(self, task_id: str) -> list[AgentExecutionLog]:
        stmt = (
            select(AgentExecutionLog)
            .where(AgentExecutionLog.task_id == task_id)
            .order_by(AgentExecutionLog.step_order.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_recent_failures(self, *, limit: int = 50) -> list[AgentExecutionLog]:
        """Useful for a future ops dashboard: 'show recent agent failures.'"""
        from models.agent_execution_log import AgentExecutionStatus

        stmt = (
            select(AgentExecutionLog)
            .where(AgentExecutionLog.status == AgentExecutionStatus.FAILED)
            .order_by(AgentExecutionLog.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
