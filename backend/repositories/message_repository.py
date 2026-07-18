"""
repositories/message_repository.py
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.message import Message
from repositories.base_repository import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Message)

    def list_for_conversation(self, conversation_id: UUID, *, limit: int = 200) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
