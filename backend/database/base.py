"""
database/base.py

WHY THIS FILE EXISTS
---------------------
Every ORM model needs a common declarative base class to register with, and
almost every table in this system shares the same three columns (id,
created_at, updated_at). Defining that once here, as a mixin, avoids
copy-pasted boilerplate across 7+ model files and guarantees consistent
primary-key and timestamp behavior across the whole schema.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
DRY (Don't Repeat Yourself) via mixins, and the "Active Record vs. Data
Mapper" distinction — SQLAlchemy's declarative base is a Data Mapper style
ORM, which is why models/ stays free of query logic (that lives in
repositories/, not on the model classes themselves).

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
Every future table (embeddings, knowledge_graph_nodes, quiz_history, etc.)
will inherit `Base` and `TimestampMixin` exactly like Phase 1's models do —
no changes needed here for later phases.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in the application."""

    pass


class UUIDPrimaryKeyMixin:
    """
    Gives every table a UUID primary key instead of an auto-increment
    integer.

    WHY UUIDs: this system will eventually sync/reference records across
    multiple storage engines (Postgres, the vector store, the graph store).
    UUIDs generated client-side (or via server default) avoid collisions
    across those systems and avoid leaking sequential row counts.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Adds created_at / updated_at columns, maintained by the database itself."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
