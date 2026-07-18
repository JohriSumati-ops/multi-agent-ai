"""
schemas/conversation.py

Request/response contracts for Conversations and their child Messages.
"""

from __future__ import annotations

from pydantic import BaseModel

from schemas.base import TimestampedSchema


class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    document_ids: list[str] = []


class ConversationOut(TimestampedSchema):
    owner_id: str
    title: str
    document_ids: list[str]
