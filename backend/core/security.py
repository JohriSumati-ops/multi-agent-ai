"""
core/security.py

Security helpers for password hashing and JWT authentication.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings
from core.exceptions import UnauthorizedError


_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT.
    """

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
    }

    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    print("\n" + "=" * 80)
    print("JWT CREATED")
    print("=" * 80)
    print("SECRET KEY:")
    print(settings.SECRET_KEY)
    print()
    print("TOKEN:")
    print(token)
    print("=" * 80 + "\n")

    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.
    """

    print("\n" + "=" * 80)
    print("JWT VALIDATION")
    print("=" * 80)
    print("SECRET KEY:")
    print(settings.SECRET_KEY)
    print()
    print("TOKEN RECEIVED:")
    print(token)
    print("=" * 80)

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        print("\nJWT PAYLOAD:")
        print(payload)
        print("=" * 80 + "\n")

        if "sub" not in payload:
            raise UnauthorizedError("Token payload missing subject claim")

        return payload

    except JWTError as exc:
        print("\nJWT ERROR:")
        print(type(exc).__name__)
        print(exc)
        print("=" * 80 + "\n")

        raise UnauthorizedError(
            "Invalid or expired authentication token"
        ) from exc