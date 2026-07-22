"""
api/deps.py

WHY THIS FILE EXISTS
---------------------
Phase 1 requirement: "Repositories should never be directly accessed by
routers" and "Use dependency injection everywhere." This module is the one
place that wires FastAPI's `Depends()` system to the service layer, so
every router imports its dependencies from here rather than constructing
services/repositories inline.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Composition Root: this is the one place in the app that knows how to
assemble a `Session` into a fully-constructed `UserService` (and, in later
phases, every other service). Routers depend on abstractions
(`Depends(get_user_service)`) rather than knowing how to build their
dependencies themselves.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
`get_current_user` is a ready-made dependency stub for Phase 2's protected
routes. Every future service (DocumentService, ConversationService,
QuizService) gets its own `get_x_service` factory function here, following
the same pattern as `get_user_service`.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.exceptions import UnauthorizedError
from core.security import decode_access_token
from database.session import get_db
from models.user import User
from repositories.user_repository import UserRepository
from services.document_service import DocumentService
from services.memory_manager import MemoryManager
from services.semantic_search_service import SemanticSearchService
from services.user_service import UserService
from services.working_memory_service import WorkingMemoryService

DBSession = Annotated[Session, Depends(get_db)]
bearer_scheme = HTTPBearer(auto_error=True)

def get_user_service(db: DBSession) -> UserService:
    return UserService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_document_service(db: DBSession) -> DocumentService:
    return DocumentService(db)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


def get_semantic_search_service(db: DBSession) -> SemanticSearchService:
    return SemanticSearchService(db)


SemanticSearchServiceDep = Annotated[SemanticSearchService, Depends(get_semantic_search_service)]


def get_working_memory_service() -> WorkingMemoryService:
    """
    Deliberately takes no `db` dependency and is constructed fresh per
    request, per docs/Phase4.md Section 3.1 — this is what makes working
    memory "automatically cleared" true without any explicit teardown code.
    """
    return WorkingMemoryService()


WorkingMemoryServiceDep = Annotated[WorkingMemoryService, Depends(get_working_memory_service)]


def get_memory_manager(db: DBSession, working_memory: WorkingMemoryServiceDep) -> MemoryManager:
    return MemoryManager(db, working_memory=working_memory)


MemoryManagerDep = Annotated[MemoryManager, Depends(get_memory_manager)]


def get_current_user(
    db: DBSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
) -> User:

    token = credentials.credentials

    payload = decode_access_token(token)

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Token payload missing subject claim")

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise UnauthorizedError("Token subject is not a valid user identifier") from exc

    user = UserRepository(db).get(user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
