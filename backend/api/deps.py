"""
api/deps.py

Dependency injection helpers.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from core.exceptions import UnauthorizedError
from core.security import decode_access_token
from database.session import get_db
from models.user import User
from repositories.user_repository import UserRepository
from services.document_service import DocumentService
from services.user_service import UserService


DBSession = Annotated[Session, Depends(get_db)]


def get_user_service(db: DBSession) -> UserService:
    return UserService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_document_service(db: DBSession) -> DocumentService:
    return DocumentService(db)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


def get_current_user(
    db: DBSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """
    Resolve the authenticated user from the Authorization header.
    Expected header:

        Authorization: Bearer <JWT>
    """

    if authorization is None:
        raise UnauthorizedError("Missing Authorization header")

    authorization = authorization.strip()

    if not authorization.startswith("Bearer "):
        raise UnauthorizedError(
            "Authorization header must start with 'Bearer '"
        )

    token = authorization[7:].strip()

    payload = decode_access_token(token)

    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("Token missing subject")

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise UnauthorizedError("Invalid token subject")

    user = UserRepository(db).get(user_id)

    if user is None:
        raise UnauthorizedError("User not found")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]