"""
api/routes/auth.py — Phase 2 addition

WHY THIS FILE EXISTS
---------------------
See `schemas/auth.py`'s docstring: Phase 1 built every primitive this route
needs (`UserService.register_user`, `UserService.authenticate`,
`create_access_token`) but never exposed them over HTTP, since Phase 1's
scope was explicitly "auth skeleton only." Phase 2's document upload
endpoint requires a real, authenticated `owner_id`, which is what makes
wiring these two routes now a necessary, minimal extension rather than
scope creep.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import DBSession
from core.security import create_access_token
from schemas.auth import LoginRequest, TokenResponse
from schemas.base import APIResponse
from schemas.user import UserCreate, UserOut
from services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=APIResponse[UserOut], status_code=201)
def register(payload: UserCreate, db: DBSession) -> APIResponse[UserOut]:
    user = UserService(db).register_user(payload)
    return APIResponse[UserOut](success=True, data=UserOut.model_validate(user))


@router.post("/login", response_model=APIResponse[TokenResponse])
def login(payload: LoginRequest, db: DBSession) -> APIResponse[TokenResponse]:
    user = UserService(db).authenticate(payload.email, payload.password)
    token = create_access_token(subject=str(user.id))
    return APIResponse[TokenResponse](success=True, data=TokenResponse(access_token=token))
