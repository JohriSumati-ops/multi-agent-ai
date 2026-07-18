"""
repositories/document_repository.py

Adds owner-scoped and status-scoped queries — every future ingestion
pipeline step (PDF Parsing Agent, Embedding Agent) will need to fetch
"documents currently in status X" to pick up work.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.document import Document, DocumentStatus
from repositories.base_repository import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Document)

    def list_for_owner(self, owner_id: UUID, *, limit: int = 100, offset: int = 0) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_by_status(self, status: DocumentStatus, *, limit: int = 100) -> list[Document]:
        """Used by future ingestion workers to find documents awaiting processing."""
        stmt = select(Document).where(Document.status == status).limit(limit)
        return list(self.db.execute(stmt).scalars().all())
