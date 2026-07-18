"""
database/session.py

WHY THIS FILE EXISTS
---------------------
Connection pooling and session lifecycle management is infrastructure, not
business logic — it should exist in exactly one place, be configured from
`core/config.py`, and be exposed to the rest of the app only through a
narrow, FastAPI-dependency-friendly interface (`get_db`). Nothing outside
this file should call `create_engine` or `sessionmaker`.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Resource management via context managers / generator-based dependency
injection — `get_db` guarantees a session is always closed (even on
exception), which is the same "acquire/release" discipline used for file
handles or network sockets.

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
The retrieval layer's chunk-lookup queries, the knowledge graph agent's
Postgres-side bookkeeping, and every repository added in later phases will
all go through `get_db` exactly like Phase 1's UserRepository does — this
file does not need to change as the schema grows.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings
from core.logging import get_logger

logger = get_logger("database")

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # detects stale connections before they cause errors
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and guarantees
    cleanup.

    Usage in a router:
        def endpoint(db: Session = Depends(get_db)): ...

    Usage in Phase 1 is indirect — routers depend on services, services
    depend on repositories, repositories depend on this. Routers should
    never import this directly (see api/deps.py).
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        logger.exception("Database session rolled back due to an exception")
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Lightweight connectivity check used by the /health endpoint.

    Returns False rather than raising, so the health endpoint can report a
    degraded status instead of crashing.
    """
    from sqlalchemy import text

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False
