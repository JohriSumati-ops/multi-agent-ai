"""
tests/test_user_service.py

Exercises the one full vertical slice built in Phase 1 (model -> schema ->
repository -> service) even though no HTTP route calls it yet — this is
what "testability" as a stated Phase 1 priority actually looks like in
practice: business logic is verifiable without spinning up the API layer.
"""

from __future__ import annotations

import pytest

from core.exceptions import ConflictError
from models.learning_profile import LearningProfile
from schemas.user import UserCreate
from services.user_service import UserService


def test_register_user_creates_user_and_learning_profile(db_session) -> None:
    service = UserService(db_session)
    user = service.register_user(
        UserCreate(email="agamya@example.com", password="password123", full_name="Agamya")
    )

    assert user.id is not None
    assert user.email == "agamya@example.com"
    assert user.hashed_password != "password123"  # must be hashed, never stored plain

    profile = (
        db_session.query(LearningProfile).filter(LearningProfile.user_id == user.id).one_or_none()
    )
    assert profile is not None


def test_register_user_rejects_duplicate_email(db_session) -> None:
    service = UserService(db_session)
    service.register_user(UserCreate(email="dupe@example.com", password="password123"))

    with pytest.raises(ConflictError):
        service.register_user(UserCreate(email="dupe@example.com", password="anotherpassword"))
