"""
tests/test_phase6_agents.py

Exercises the five Phase 6 agents through BaseAgent.run(), exactly like
every other agent test in this project.
"""

from __future__ import annotations

import json

from agents.citation_agent import CitationAgent
from agents.question_answering_agent import QuestionAnsweringAgent
from agents.reasoning_agent import ReasoningAgent
from agents.research_agent import ResearchAgent
from agents.summarization_agent import SummarizationAgent
from core.agent_bus import TaskContext
from llm.base_llm import LLMResponse
from models.user import User
from services.long_term_memory_service import LongTermMemoryService
from tests.fakes import FakeLLMBackend


def _make_user(db_session, email="agent6@example.com") -> User:
    user = User(email=email, hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_research_agent_requires_query(db_session) -> None:
    context = TaskContext(original_query="")
    context.intermediate_results["db"] = db_session
    context.intermediate_results["user_id"] = None
    result = ResearchAgent().run(context)
    assert result.success is False


def test_research_agent_full_pipeline(db_session) -> None:
    user = _make_user(db_session)
    memory = LongTermMemoryService(db_session).write(user.id, "Recursion solves problems via self-reference.")

    fake_backend = FakeLLMBackend()
    fake_backend.queued_responses = [
        LLMResponse(
            content=json.dumps(
                {
                    "answer": "Recursion solves problems via self-reference.",
                    "sources_used": [{"chunk_id": str(memory.id)}],
                    "confidence": 0.85,
                    "reasoning_summary": "From memory.",
                    "memory_references": [str(memory.id)],
                }
            ),
            model_name="fake",
        )
    ]

    context = TaskContext(original_query="")
    context.intermediate_results["db"] = db_session
    context.intermediate_results["user_id"] = user.id
    context.intermediate_results["query"] = "How does recursion work?"
    context.intermediate_results["llm_backend"] = fake_backend
    context.intermediate_results["similarity_threshold"] = -1.0

    result = ResearchAgent().run(context)
    assert result.success is True
    assert result.output.used_llm is True
    assert result.output.answer.answer == "Recursion solves problems via self-reference."


def test_question_answering_agent_scopes_to_document(db_session) -> None:
    user = _make_user(db_session)
    context = TaskContext(original_query="")
    context.intermediate_results["db"] = db_session
    context.intermediate_results["user_id"] = user.id
    context.intermediate_results["query"] = "no data exists for this"
    context.intermediate_results["llm_backend"] = FakeLLMBackend()

    result = QuestionAnsweringAgent().run(context)
    assert result.success is True
    assert result.output.used_llm is False  # no context -> fallback, no LLM call


def test_summarization_agent_uses_default_query_when_absent(db_session) -> None:
    user = _make_user(db_session)
    context = TaskContext(original_query="")
    context.intermediate_results["db"] = db_session
    context.intermediate_results["user_id"] = user.id
    # deliberately omit "query"
    context.intermediate_results["llm_backend"] = FakeLLMBackend()

    result = SummarizationAgent().run(context)
    assert result.success is True  # should not fail validation despite missing query


def test_citation_agent_resolves_ids(db_session) -> None:
    user = _make_user(db_session)
    memory = LongTermMemoryService(db_session).write(user.id, "A fact worth citing.")

    context = TaskContext(original_query="")
    context.intermediate_results["db"] = db_session
    context.intermediate_results["chunk_ids"] = [str(memory.id)]

    result = CitationAgent().run(context)
    assert result.success is True
    assert len(result.output.citations) == 1


def test_citation_agent_requires_chunk_ids(db_session) -> None:
    context = TaskContext(original_query="")
    context.intermediate_results["db"] = db_session
    result = CitationAgent().run(context)
    assert result.success is False


def test_reasoning_agent_analyzes_evidence(db_session) -> None:
    user = _make_user(db_session)
    LongTermMemoryService(db_session).write(user.id, "Coffee improves alertness in most adults.")
    LongTermMemoryService(db_session).write(user.id, "Coffee does not improve alertness for everyone.")

    context = TaskContext(original_query="")
    context.intermediate_results["db"] = db_session
    context.intermediate_results["user_id"] = user.id
    context.intermediate_results["query"] = "coffee and alertness"
    context.intermediate_results["similarity_threshold"] = -1.0

    result = ReasoningAgent().run(context)
    assert result.success is True
    assert result.output.synthesis.evidence_count == 2


def test_reasoning_agent_makes_no_llm_call(db_session) -> None:
    """ReasoningAgent's entire value is being LLM-free — verified structurally."""
    import agents.reasoning_agent as module

    source = open(module.__file__).read()
    assert "llm_service" not in source.lower().replace("llm_backend", "")
