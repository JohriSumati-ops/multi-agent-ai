"""
tests/test_context_builder.py
"""

from __future__ import annotations

from models.user import User
from orchestration.context_builder import ContextBuilder
from services.memory_manager import MemoryManager
from services.semantic_search_service import SemanticSearchService
from services.working_memory_service import WorkingMemoryService


def _make_user(db_session) -> User:
    user = User(email="ctxbuilder@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_builder(db_session, working_memory=None) -> ContextBuilder:
    wm = working_memory or WorkingMemoryService()
    return ContextBuilder(
        working_memory=wm,
        memory_manager=MemoryManager(db_session, working_memory=wm),
        search_service=SemanticSearchService(db_session),
    )


def test_build_with_no_prior_data_returns_empty_context(db_session) -> None:
    user = _make_user(db_session)
    builder = _make_builder(db_session)

    context = builder.build(user_id=user.id, request_text="explain binary trees")
    assert context.short_term_memories == []
    assert context.long_term_memory_hits == []
    assert context.retrieved_chunks == []


def test_build_includes_working_memory_snapshot(db_session) -> None:
    user = _make_user(db_session)
    wm = WorkingMemoryService()
    wm.remember("last_topic", "recursion")
    builder = _make_builder(db_session, working_memory=wm)

    context = builder.build(user_id=user.id, request_text="explain recursion")
    assert context.working_memory_snapshot == {"last_topic": "recursion"}


def test_build_includes_short_term_memory(db_session) -> None:
    user = _make_user(db_session)
    builder = _make_builder(db_session)
    builder.memory_manager.remember(user.id, "User asked about linked lists", persist_long_term=False)

    context = builder.build(user_id=user.id, request_text="linked lists")
    assert "User asked about linked lists" in context.short_term_memories


def test_build_includes_long_term_memory_hits(db_session) -> None:
    user = _make_user(db_session)
    builder = _make_builder(db_session)
    builder.memory_manager.remember(
        user.id, "User struggles with recursion base cases", persist_long_term=True
    )

    context = builder.build(user_id=user.id, request_text="recursion base cases", top_k_memory=5)
    assert len(context.long_term_memory_hits) == 1


def test_source_summary_reports_counts(db_session) -> None:
    user = _make_user(db_session)
    builder = _make_builder(db_session)
    builder.memory_manager.remember(user.id, "some memory", persist_long_term=False)

    context = builder.build(user_id=user.id, request_text="query")
    summary = context.source_summary()
    assert summary["short_term_memories"] == 1
    assert "working_memory_keys" in summary


def test_build_does_not_leak_other_users_memory(db_session) -> None:
    user_a = _make_user(db_session)
    user_b = User(email="ctxbuilder2@example.com", hashed_password="h")
    db_session.add(user_b)
    db_session.commit()
    db_session.refresh(user_b)

    builder = _make_builder(db_session)
    builder.memory_manager.remember(user_a.id, "user A's private memory", persist_long_term=True)

    context = builder.build(user_id=user_b.id, request_text="private memory", top_k_memory=5)
    assert context.long_term_memory_hits == []
