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

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from core.exceptions import UnauthorizedError
from core.security import decode_access_token
from database.session import get_db
from models.user import User
from repositories.user_repository import UserRepository
from services.user_service import UserService

DBSession = Annotated[Session, Depends(get_db)]


def get_user_service(db: DBSession) -> UserService:
    return UserService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_current_user(
    db: DBSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """
    Resolves the authenticated user from a Bearer token.

    Not wired into any route in Phase 1 (no protected business endpoints
    exist yet), but defined now so Phase 2's first protected route can add
    `user: Annotated[User, Depends(get_current_user)]` to its signature
    with zero additional plumbing.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token payload missing subject claim")

    user = UserRepository(db).get(user_id)
    if user is None:
        raise UnauthorizedError("User for this token no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
