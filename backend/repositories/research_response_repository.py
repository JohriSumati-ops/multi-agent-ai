"""
repositories/research_response_repository.py — Phase 6
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.research_response import ResearchResponse
from repositories.base_repository import BaseRepository


class ResearchResponseRepository(BaseRepository[ResearchResponse]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ResearchResponse)

    def list_for_user(self, user_id: UUID, *, limit: int = 20) -> list[ResearchResponse]:
        stmt = (
            select(ResearchResponse)
            .where(ResearchResponse.user_id == user_id)
            .order_by(ResearchResponse.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_owned(self, response_id: UUID, user_id: UUID) -> ResearchResponse | None:
        response = self.get(response_id)
        if response is None or response.user_id != user_id:
            return None
        return response
