"""
api/routes/version.py

Simple metadata endpoint — lets a client (or a smoke test in CI) confirm
which build/environment it's talking to without hitting anything stateful.
"""

from fastapi import APIRouter

from core.config import settings
from schemas.base import APIResponse, VersionInfo

router = APIRouter(tags=["system"])


@router.get("/version", response_model=APIResponse[VersionInfo])
def get_version() -> APIResponse[VersionInfo]:
    return APIResponse[VersionInfo](
        success=True,
        data=VersionInfo(
            app_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
        ),
    )
