"""
repositories/llm_usage_log_repository.py — Phase 6
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.llm_usage_log import LLMUsageLog
from repositories.base_repository import BaseRepository


class LLMUsageLogRepository(BaseRepository[LLMUsageLog]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, LLMUsageLog)

    def total_tokens_for_user(self, user_id: UUID) -> dict[str, int]:
        stmt = select(
            func.coalesce(func.sum(LLMUsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(LLMUsageLog.completion_tokens), 0),
        ).where(LLMUsageLog.user_id == user_id)
        prompt_total, completion_total = self.db.execute(stmt).one()
        return {
            "prompt_tokens": int(prompt_total),
            "completion_tokens": int(completion_total),
            "total_tokens": int(prompt_total) + int(completion_total),
        }

    def list_for_task(self, task_id: str) -> list[LLMUsageLog]:
        stmt = select(LLMUsageLog).where(LLMUsageLog.task_id == task_id).order_by(LLMUsageLog.created_at.asc())
        return list(self.db.execute(stmt).scalars().all())
