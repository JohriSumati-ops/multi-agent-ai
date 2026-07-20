"""
core/exceptions.py

WHY THIS FILE EXISTS
---------------------
Raising bare `Exception` or `HTTPException` from deep inside a service or
repository couples business logic to the web framework and loses semantic
meaning (a "document not found" and a "database timed out" both just look
like generic errors to the caller). This module defines a small, specific
exception hierarchy that any layer (repository, service, agent) can raise,
and which the global exception handler (middleware/error_handler.py) knows
how to translate into a consistent HTTP response.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Domain-specific exception hierarchies + a single translation boundary at the
edge of the system (the API layer). Business logic never imports
`fastapi.HTTPException` — that keeps services testable and reusable outside
an HTTP context (e.g., from a CLI script or a background worker).

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Agent failures (Phase 3+) will raise `AgentExecutionError`, retrieval
failures will raise `RetrievalError`, etc. Because they all inherit from
`AppException`, the global handler doesn't need to know about every new
exception type future phases introduce.
"""

from __future__ import annotations


class AppException(Exception):
    """Base class for every application-defined exception."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


# --------------------------------------------------------------------- #
# 4xx — client/request errors
# --------------------------------------------------------------------- #
class NotFoundError(AppException):
    status_code = 404
    error_code = "not_found"


class ValidationAppError(AppException):
    status_code = 422
    error_code = "validation_error"


class UnauthorizedError(AppException):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(AppException):
    status_code = 403
    error_code = "forbidden"


class ConflictError(AppException):
    status_code = 409
    error_code = "conflict"


# --------------------------------------------------------------------- #
# 5xx — server/infrastructure errors
# --------------------------------------------------------------------- #
class DatabaseError(AppException):
    status_code = 500
    error_code = "database_error"


class ConfigurationError(AppException):
    status_code = 500
    error_code = "configuration_error"


# --------------------------------------------------------------------- #
# Forward-looking, unused in Phase 1, defined now so later phases don't
# need to modify this file's structure — only add new leaf classes.
# --------------------------------------------------------------------- #
class AgentExecutionError(AppException):
    status_code = 500
    error_code = "agent_execution_error"


class RetrievalError(AppException):
    status_code = 500
    error_code = "retrieval_error"


class LLMProviderError(AppException):
    status_code = 502
    error_code = "llm_provider_error"


# --------------------------------------------------------------------- #
# Phase 2 — document processing errors. All are 4xx because in every
# case the *input* (the uploaded file) is what's at fault, not the server.
# --------------------------------------------------------------------- #
class UnsupportedFileTypeError(AppException):
    status_code = 415
    error_code = "unsupported_file_type"


class FileTooLargeError(AppException):
    status_code = 413
    error_code = "file_too_large"


class CorruptedDocumentError(AppException):
    status_code = 422
    error_code = "corrupted_document"


class EmptyDocumentError(AppException):
    status_code = 422
    error_code = "empty_document"


class EncryptedDocumentError(AppException):
    status_code = 422
    error_code = "encrypted_document"
