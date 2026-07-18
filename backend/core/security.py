"""
core/security.py

WHY THIS FILE EXISTS
---------------------
Phase 1 does not implement login/signup endpoints, but every future phase
needs a stable place to hash passwords and mint/verify JWTs. Defining that
contract now means the User model, repository, and future auth routes can
all be built against a fixed interface.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Separation of "security primitives" (hashing, token encode/decode) from
"auth flow" (login endpoint, refresh endpoint). This file is the former —
low-level, well-tested primitives with no HTTP awareness.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
`get_current_user` (built on `decode_access_token`) will become a FastAPI
dependency injected into every business route from Phase 2 onward, so agents
always execute in the context of an authenticated user (required for
per-user memory, learning profile, and document scoping).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings
from core.exceptions import UnauthorizedError

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """One-way hash a plaintext password for storage."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Mint a signed JWT for `subject` (typically the user's UUID as a string).

    Not called from anywhere yet in Phase 1 — provided so Phase 2's login
    endpoint has a ready-made, tested implementation to call.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT, raising UnauthorizedError on any failure.

    Deliberately raises our own AppException subclass rather than letting
    `JWTError` leak upward — see core/exceptions.py for why.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired authentication token") from exc
