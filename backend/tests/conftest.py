"""
tests/conftest.py

WHY THIS FILE EXISTS
---------------------
Tests must never touch a real PostgreSQL instance — that makes them slow,
order-dependent, and impossible to run in CI without provisioning
infrastructure. This fixture overrides the `get_db` dependency with an
in-memory SQLite session for the duration of the test suite, and overrides
the FastAPI dependency graph accordingly.

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Dependency Injection is precisely what makes this possible: because routers
depend on `Depends(get_db)` rather than importing a hardcoded engine,
swapping the real database for a test database is a one-line
`app.dependency_overrides` call, with zero changes to application code.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import models  # noqa: F401 — registers mappers, see models/__init__.py
from database.base import Base
from database.session import get_db
from main import app

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
