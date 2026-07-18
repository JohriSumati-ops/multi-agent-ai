"""
middleware/logging_middleware.py

WHY THIS FILE EXISTS
---------------------
Phase 1 requirement: "API Logs" as a distinct log category. This middleware
logs every request/response pair (method, path, status code, duration)
through the `app.api` logger channel defined in core/logging.py, giving
consistent, structured API-level observability independent of anything a
specific route does.
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.logging import get_logger

logger = get_logger("api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        started_at = time.perf_counter()

        response = await call_next(request)

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "%s %s -> %s (%dms) [request_id=%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
