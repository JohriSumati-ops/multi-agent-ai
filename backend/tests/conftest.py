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
from sqlalchemy.pool import StaticPool

import models  # noqa: F401 — registers mappers, see models/__init__.py
from core.config import settings
from database.base import Base
from database.session import get_db
from main import app
from retrieval.embedder import EmbeddingService
from retrieval.vector_store import reset_memory_vector_store, reset_vector_store
from memory.session_memory import reset_session_memory
from orchestration.agent_registry import reset_agent_registry
from tests.fakes import FakeEmbeddingBackend

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    """
    Phase 2 addition: redirects every test's document uploads to a
    per-test temp directory instead of the real `settings.UPLOAD_DIR`.
    `autouse=True` so no individual test needs to remember to request it —
    accidentally writing test files into the real storage/uploads/
    directory would be a silent, easy-to-miss bug otherwise.
    """
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))


@pytest.fixture(autouse=True)
def isolated_embedding_service(tmp_path, monkeypatch):
    """
    Phase 3 addition (extended in Phase 4): every test gets a fresh
    `EmbeddingService` singleton backed by `FakeEmbeddingBackend`
    (deterministic, no network access to a model hub required — see
    retrieval/embedder.py and docs/Phase3.md Section 19), a fresh
    `FAISSVectorStore` singleton for documents, AND (Phase 4) a fresh,
    SEPARATE `FAISSVectorStore` singleton for memory, each pointed at its
    own per-test temp directory so the two indexes can never collide on
    disk (see docs/Phase4.md Section 11's explicit callout of this risk).
    Also resets the Phase 4 session memory singleton for the same reason.

    `autouse=True` for the same reason as `isolated_upload_dir` above: this
    kind of cross-test state leakage is exactly the class of bug that's
    easy to introduce accidentally and hard to debug later.
    """
    monkeypatch.setattr(settings, "VECTOR_STORE_URL", str(tmp_path / "vector_store"))
    monkeypatch.setattr(settings, "MEMORY_VECTOR_STORE_URL", str(tmp_path / "memory_vector_store"))
    EmbeddingService.reset_instance()
    EmbeddingService.get_instance(FakeEmbeddingBackend())
    reset_vector_store()
    reset_memory_vector_store()
    reset_session_memory()
    reset_agent_registry()
    yield
    EmbeddingService.reset_instance()
    reset_vector_store()
    reset_memory_vector_store()
    reset_session_memory()
    reset_agent_registry()


@pytest.fixture()
def db_session():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


@pytest.fixture()
def auth_headers(client: TestClient) -> dict:
    """
    Registers and logs in a fresh user, returning a ready-to-use
    Authorization header dict — every Phase 2 document test needs an
    authenticated user, so this is the shared setup for all of them.
    """
    client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "password123", "full_name": "Student"},
    )
    login_response = client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "password123"}
    )
    token = login_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
