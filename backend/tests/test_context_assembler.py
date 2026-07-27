"""
tests/test_context_assembler.py
"""

from __future__ import annotations

from models.user import User
from reasoning.context_assembler import ContextAssembler
from services.memory_manager import MemoryManager
from services.semantic_search_service import SemanticSearchService


def _make_user(db_session, email="ctxassm@example.com") -> User:
    user = User(email=email, hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_assembler(db_session) -> ContextAssembler:
    return ContextAssembler(search_service=SemanticSearchService(db_session), memory_manager=MemoryManager(db_session))


def test_assemble_with_no_data_returns_empty_context(db_session) -> None:
    user = _make_user(db_session)
    assembler = _make_assembler(db_session)
    context = assembler.assemble(user_id=user.id, query="anything", token_budget=1000)
    assert context.is_empty is True


def test_assemble_includes_long_term_memory(db_session) -> None:
    user = _make_user(db_session)
    assembler = _make_assembler(db_session)
    assembler.memory_manager.remember(user.id, "User struggles with recursion.", persist_long_term=True)

    context = assembler.assemble(user_id=user.id, query="recursion", token_budget=1000, similarity_threshold=-1.0)
    assert len(context.items) == 1
    assert context.items[0].source_type == "memory"


def test_assemble_respects_token_budget(db_session) -> None:
    user = _make_user(db_session)
    assembler = _make_assembler(db_session)
    long_text = " ".join(f"word{i}" for i in range(50))
    assembler.memory_manager.remember(user.id, long_text, persist_long_term=True)

    context = assembler.assemble(user_id=user.id, query="word", token_budget=10, similarity_threshold=-1.0)
    assert context.approx_token_count <= 10
    assert context.items[0].was_compressed is True


def test_assemble_reports_excluded_items_when_budget_exhausted(db_session) -> None:
    user = _make_user(db_session)
    assembler = _make_assembler(db_session)
    for i in range(3):
        assembler.memory_manager.remember(user.id, f"Distinct memory content number {i} about topic X.", persist_long_term=True)

    # Budget large enough for ~1 item's worth of words only.
    context = assembler.assemble(user_id=user.id, query="topic X", token_budget=8, similarity_threshold=-1.0)
    assert len(context.items) >= 1
    total_seen = len(context.items) + context.excluded_count
    assert total_seen == 3


def test_chunk_ids_and_memory_ids_partition_correctly(db_session) -> None:
    user = _make_user(db_session)
    assembler = _make_assembler(db_session)
    assembler.memory_manager.remember(user.id, "A memory about graphs.", persist_long_term=True)

    context = assembler.assemble(user_id=user.id, query="graphs", token_budget=1000, similarity_threshold=-1.0)
    assert len(context.memory_ids()) == 1
    assert len(context.chunk_ids()) == 0


def test_render_for_prompt_includes_source_tags(db_session) -> None:
    user = _make_user(db_session)
    assembler = _make_assembler(db_session)
    assembler.memory_manager.remember(user.id, "Something memorable about stacks.", persist_long_term=True)

    context = assembler.assemble(user_id=user.id, query="stacks", token_budget=1000, similarity_threshold=-1.0)
    rendered = context.render_for_prompt()
    assert "chunk_id=" in rendered
    assert "Something memorable about stacks." in rendered


def test_assemble_does_not_leak_other_users_data(db_session) -> None:
    user_a = _make_user(db_session, "ctxa@example.com")
    user_b = _make_user(db_session, "ctxb@example.com")
    assembler = _make_assembler(db_session)
    assembler.memory_manager.remember(user_a.id, "User A's confidential research notes.", persist_long_term=True)

    context = assembler.assemble(user_id=user_b.id, query="confidential research notes", token_budget=1000, similarity_threshold=-1.0)
    assert context.is_empty is True
