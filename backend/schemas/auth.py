"""
schemas/auth.py

WHY THIS FILE EXISTS
---------------------
Phase 1 built the auth *primitives* (`core/security.py`) but no HTTP
route ever called them. Phase 2 needs an authenticated `owner_id` to
attach to uploaded documents, which is the first real requirement that
makes "there's no way to log in yet" a blocking gap rather than a
theoretical one. This file defines the minimal request/response contracts
for that flow — see `api/routes/auth.py`.

This is a deliberate, small, flagged extension of Phase 1's scope (see
Phase 2's changelog), not a redesign: every piece it depends on
(`hash_password`, `verify_password`, `create_access_token`, `UserService`)
already existed and was already tested.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
