"""
middleware/error_handler.py

WHY THIS FILE EXISTS
---------------------
Phase 1 requirement: a global exception handler producing a consistent API
response format, covering validation errors, database errors, HTTP errors,
and our own AppException hierarchy. Without this, every router would need
its own try/except, and clients would see inconsistent error shapes
depending on which layer raised the exception.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Centralized error translation at the system boundary (see
core/exceptions.py's docstring) — this is the ONE place `AppException`
subclasses get turned into HTTP responses. Business logic (services,
repositories, future agents) never needs to know it's running inside a web
framework.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
When `AgentExecutionError` or `RetrievalError` are actually raised by
future agents, they're already handled here for free — no changes needed
to this file when Phase 3+ introduces those code paths.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.exceptions import AppException
from core.logging import get_logger

logger = get_logger("error")


def _error_response(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": {"code": code, "message": message, "details": details or {}},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Call once from main.py during app construction."""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        logger.warning("AppException on %s %s: %s", request.method, request.url.path, exc.message)
        return _error_response(exc.status_code, exc.error_code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed",
            {"errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        logger.info("HTTPException on %s %s: %s", request.method, request.url.path, exc.detail)
        return _error_response(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error on %s %s", request.method, request.url.path)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "database_error",
            "A database error occurred. Please try again.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        # Last-resort catch-all so an unanticipated bug never leaks a raw
        # traceback to a client — it still gets fully logged server-side.
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
        )
