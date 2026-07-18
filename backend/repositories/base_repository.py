"""
repositories/base_repository.py

WHY THIS FILE EXISTS
---------------------
Nearly every repository needs the same four operations (get by id, list,
create, delete). Writing that CRUD boilerplate seven times (once per model)
would violate DRY and create seven slightly-inconsistent implementations.
This generic base class implements it once; concrete repositories add only
their model-specific queries.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
This is the Repository Pattern combined with Python generics
(`Generic[ModelType]`): the base class is fully type-safe for whichever
model a subclass parameterizes it with, so `UserRepository(BaseRepository[User])`
gets `get(id) -> User | None`, not `-> Any`.

Crucially: repositories are the ONLY code in the entire application allowed
to import SQLAlchemy query constructs. Routers call services; services call
repositories; repositories call the database. This one-directional
dependency chain is what makes the storage layer swappable later.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Every repository added in later phases (EmbeddingRepository,
KnowledgeGraphNodeRepository, QuizHistoryRepository, ...) will subclass this
exact base class, exactly like Phase 1's repositories do.
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: Session, model: type[ModelType]) -> None:
        self.db = db
        self.model = model

    def get(self, id: UUID | str) -> ModelType | None:
        return self.db.get(self.model, id)

    def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelType]:
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.commit()

    def commit_refresh(self, obj: ModelType) -> ModelType:
        """Call after mutating fields on an already-tracked object."""
        self.db.commit()
        self.db.refresh(obj)
        return obj
