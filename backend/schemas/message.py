"""
schemas/message.py

Request/response contracts for individual chat messages.
"""

from __future__ import annotations

from pydantic import BaseModel

from models.message import MessageRole
from schemas.base import TimestampedSchema


class MessageCreate(BaseModel):
    conversation_id: str
    role: MessageRole
    content: str


class MessageOut(TimestampedSchema):
    conversation_id: str
    role: MessageRole
    content: str
    agent_name: str | None = None
