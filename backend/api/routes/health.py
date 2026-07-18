"""
api/routes/health.py

WHY THIS ROUTE EXISTS
-----------------------
Standard operational requirement for any deployable service: load
balancers, container orchestrators, and uptime monitors all need a cheap
endpoint to poll. It also doubles as a smoke test that the database
connection is actually alive, not just that the process is running.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Routers are transport-only: this handler does no business logic itself —
it delegates the actual connectivity check to
`database.session.check_database_connection` and just shapes the HTTP
response.
"""

from fastapi import APIRouter

from core.config import settings
from database.session import check_database_connection
from schemas.base import APIResponse, HealthStatus

router = APIRouter(tags=["system"])


@router.get("/health", response_model=APIResponse[HealthStatus])
def health_check() -> APIResponse[HealthStatus]:
    db_ok = check_database_connection()
    status_label = "healthy" if db_ok else "degraded"

    return APIResponse[HealthStatus](
        success=True,
        data=HealthStatus(
            status=status_label,
            database=db_ok,
            environment=settings.ENVIRONMENT,
        ),
    )
