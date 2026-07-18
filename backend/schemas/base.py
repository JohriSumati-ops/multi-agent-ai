"""
schemas/base.py

WHY THIS FILE EXISTS
---------------------
`models/` describes what's stored in the database; `schemas/` describes
what crosses the API boundary. This file defines the small set of base
classes every other schema builds on, plus the consistent response
envelope required by the "Consistent API response format" requirement.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Never expose ORM models directly over the API. Pydantic schemas are the
explicit contract with clients — they let you add/remove/rename a database
column without silently changing the API's shape (and vice versa).

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Every future response schema (DocumentOut, ConversationOut, agent
responses) wraps in `APIResponse` so the frontend can rely on one parsing
path (`response.data`, `response.error`) regardless of which endpoint it
called.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBaseSchema(BaseModel):
    """
    Base for any schema that will be constructed directly from an ORM
    model instance (`Model.model_validate(orm_obj)`).
    """

    model_config = ConfigDict(from_attributes=True)


class TimestampedSchema(ORMBaseSchema):
    """Base for output schemas of any table using TimestampMixin."""

    id: UUID
    created_at: datetime
    updated_at: datetime


class ErrorDetail(BaseModel):
    """Shape of the `error` field in APIResponse when a request fails."""

    code: str
    message: str
    details: dict = {}


class APIResponse(BaseModel, Generic[T]):
    """
    Consistent envelope for every API response in the system.

    Success:  {"success": true,  "data": {...}, "error": null}
    Failure:  {"success": false, "data": null,   "error": {...}}

    WHY a generic envelope instead of returning raw resource JSON: it gives
    the frontend one predictable shape to branch on (`success`) instead of
    inferring success/failure from HTTP status codes alone, and gives every
    endpoint a place to attach non-resource metadata later (pagination,
    request_id, etc.) without breaking existing clients.
    """

    success: bool
    data: T | None = None
    error: ErrorDetail | None = None


class HealthStatus(BaseModel):
    status: str
    database: bool
    environment: str


class VersionInfo(BaseModel):
    app_name: str
    version: str
    environment: str
