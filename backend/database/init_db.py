"""
database/init_db.py

Initializes the database schema.

This module creates every table registered with SQLAlchemy's Declarative Base.
It is executed once during FastAPI startup.
"""

from database.base import Base
from database.session import engine
import models  # noqa: F401


def init_db() -> None:
    """
    Create all database tables if they do not already exist.
    """
    Base.metadata.create_all(bind=engine)