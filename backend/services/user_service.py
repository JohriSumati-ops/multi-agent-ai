"""
services/user_service.py

WHY THIS FILE EXISTS
---------------------
Routers should never call repositories directly (see Architecture Section
3.2 and the Phase 1 "dependency injection everywhere" requirement).
Services sit between the two: they hold business rules (e.g., "creating a
user also provisions a LearningProfile") that don't belong in a repository
(pure data access) or a router (pure HTTP transport).

No user-facing routes exist yet in Phase 1 (no signup endpoint), but this
service is built now, alongside its repository and schema, so the full
vertical slice (model → schema → repository → service) is validated end to
end for at least one resource before Phase 2 adds the HTTP layer on top.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Service Layer pattern — orchestration logic that spans more than one
repository (here: UserRepository + LearningProfileRepository) belongs in a
service, not bolted onto either repository or duplicated in a router.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Phase 2's `POST /auth/register` route will call
`UserService.register_user(...)` instead of touching UserRepository
directly — the route stays a thin translation layer between HTTP and this
service.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from core.exceptions import ConflictError, UnauthorizedError
from core.security import hash_password, verify_password
from models.user import User
from repositories.learning_profile_repository import LearningProfileRepository
from repositories.user_repository import UserRepository
from schemas.user import UserCreate


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.learning_profiles = LearningProfileRepository(db)

    def register_user(self, payload: UserCreate) -> User:
        """
        Create a user and provision their LearningProfile in one
        transaction-scoped operation — this is exactly the kind of
        multi-repository orchestration that belongs in a service, not a
        repository or a router.
        """
        if self.users.get_by_email(payload.email) is not None:
            raise ConflictError(f"A user with email {payload.email} already exists")

        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        user = self.users.create(user)

        # Every user gets a LearningProfile immediately — later phases
        # (Gap Analysis, Recommendation) can then assume it always exists
        # rather than needing null-checks scattered across the codebase.
        self.learning_profiles.get_or_create(user.id)

        return user

    def get_user(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def authenticate(self, email: str, password: str) -> User:
        """
        Phase 2 addition: verifies email/password for the login endpoint.
        Uses the exact `verify_password` primitive Phase 1 built and
        tested, just never wired to an HTTP route until now.
        """
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            # Deliberately identical error for "no such user" and "wrong
            # password" — distinguishing them lets an attacker enumerate
            # valid emails.
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated")
        return user
