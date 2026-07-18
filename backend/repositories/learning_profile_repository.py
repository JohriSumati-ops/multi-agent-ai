"""
repositories/learning_profile_repository.py

`get_or_create` exists because every user should have exactly one
LearningProfile, lazily created on first access rather than requiring a
separate provisioning step at signup — simpler for callers, and safe
because of the `unique=True` constraint on `LearningProfile.user_id`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.learning_profile import LearningProfile
from repositories.base_repository import BaseRepository


class LearningProfileRepository(BaseRepository[LearningProfile]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, LearningProfile)

    def get_by_user(self, user_id: UUID) -> LearningProfile | None:
        stmt = select(LearningProfile).where(LearningProfile.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create(self, user_id: UUID) -> LearningProfile:
        profile = self.get_by_user(user_id)
        if profile is not None:
            return profile
        profile = LearningProfile(user_id=user_id)
        return self.create(profile)
