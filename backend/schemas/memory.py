"""
schemas/memory.py

Request/response contracts for the Memory resource. `MemoryCreate` is not
called from any route in Phase 1 — it exists so the future Memory Agent
(and its unit tests) has a validated contract to write against from day one.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from models.memory import MemoryType
from schemas.base import TimestampedSchema


class MemoryCreate(BaseModel):
    user_id: str
    memory_type: MemoryType
    content: str
    conversation_id: str | None = None
    document_id: str | None = None
    importance_score: float = 0.5
    expires_at: datetime | None = None


class MemoryOut(TimestampedSchema):
    user_id: str
    memory_type: MemoryType
    content: str
    conversation_id: str | None = None
    document_id: str | None = None
    importance_score: float
    expires_at: datetime | None = None
