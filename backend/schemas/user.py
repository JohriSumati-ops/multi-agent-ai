"""
schemas/user.py

Request/response contracts for the User resource. No auth routes exist yet
in Phase 1 (per the "auth skeleton only" scope), but the Create/Out split
below is what Phase 2's registration endpoint will use directly.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from schemas.base import TimestampedSchema


class UserCreate(BaseModel):
    """Input contract for user registration (not yet wired to a route)."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class UserOut(TimestampedSchema):
    """Public-facing user representation — deliberately excludes hashed_password."""

    email: EmailStr
    full_name: str | None = None
    is_active: bool
