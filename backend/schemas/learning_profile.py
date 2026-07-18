"""
schemas/learning_profile.py

Request/response contracts for the LearningProfile resource. Writes to
most of these fields will come from future agents (Gap Analysis, Quiz),
not directly from the user — `LearningProfileUpdate` is intentionally
narrow to the fields a user is allowed to set themselves.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from schemas.base import TimestampedSchema


class LearningProfileUpdate(BaseModel):
    """Fields a user may directly edit (study preferences only)."""

    preferred_difficulty: str | None = None
    preferred_language: str | None = None


class LearningProfileOut(TimestampedSchema):
    user_id: str
    weak_topics: list[str]
    strong_topics: list[str]
    quiz_accuracy: float
    revision_count: int
    learning_streak_days: int
    preferred_difficulty: str
    preferred_language: str
    last_activity_at: datetime | None = None
