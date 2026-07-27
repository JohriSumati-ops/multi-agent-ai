"""
tests/test_llm_service.py
"""

from __future__ import annotations

import time

from core.exceptions import LLMProviderError
from llm.base_llm import LLMMessage, LLMResponse
from llm.llm_service import LLMService
from models.user import User
from repositories.llm_usage_log_repository import LLMUsageLogRepository
from tests.fakes import FakeLLMBackend


def _make_user(db_session) -> User:
    user = User(email="llmsvc@example.com", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_generate_returns_response_on_success() -> None:
    backend = FakeLLMBackend()
    service = LLMService(backend)
    response = service.generate([LLMMessage(role="user", content="hi")])
    assert response.content
    assert backend.call_count == 1


def test_generate_retries_on_transient_failure() -> None:
    backend = FakeLLMBackend()
    backend.queued_responses = [LLMProviderError("network blip")]
    service = LLMService(backend, max_retries=2)
    response = service.generate([LLMMessage(role="user", content="hi")])
    assert response.content
    assert backend.call_count == 2


def test_generate_raises_after_exhausting_retries() -> None:
    backend = FakeLLMBackend()
    backend.queued_responses = [
        LLMProviderError("e1"),
        LLMProviderError("e2"),
        LLMProviderError("e3"),
    ]
    service = LLMService(backend, max_retries=2)
    try:
        service.generate([LLMMessage(role="user", content="hi")])
        assert False, "expected LLMProviderError"
    except LLMProviderError:
        pass
    assert backend.call_count == 3


def test_generate_enforces_timeout_without_blocking() -> None:
    class SlowBackend:
        provider_name = "slow"
        model_name = "slow-model"

        def generate(self, messages, **kwargs):
            time.sleep(2)
            return LLMResponse(content="too slow", model_name="slow-model")

        def embed(self, texts):
            raise NotImplementedError

    service = LLMService(SlowBackend(), timeout_seconds=0.2, max_retries=0)
    start = time.time()
    try:
        service.generate([LLMMessage(role="user", content="hi")])
        assert False, "expected LLMProviderError (timeout)"
    except LLMProviderError as e:
        assert "timed out" in str(e)
    elapsed = time.time() - start
    assert elapsed < 1.0  # must not have waited for the full 2s sleep


def test_usage_is_logged_on_success(db_session) -> None:
    user = _make_user(db_session)
    repo = LLMUsageLogRepository(db_session)
    backend = FakeLLMBackend()
    service = LLMService(backend, usage_log_repo=repo, user_id=user.id)

    service.generate([LLMMessage(role="user", content="hi")], task_id="task-abc")

    usage = repo.total_tokens_for_user(user.id)
    assert usage["total_tokens"] == 70  # 50 prompt + 20 completion, from FakeLLMBackend's default response
    logs = repo.list_for_task("task-abc")
    assert len(logs) == 1
    assert logs[0].success is True


def test_usage_is_logged_on_failure(db_session) -> None:
    user = _make_user(db_session)
    repo = LLMUsageLogRepository(db_session)
    backend = FakeLLMBackend()
    backend.queued_responses = [LLMProviderError("e1"), LLMProviderError("e2"), LLMProviderError("e3")]
    service = LLMService(backend, usage_log_repo=repo, user_id=user.id, max_retries=2)

    try:
        service.generate([LLMMessage(role="user", content="hi")], task_id="task-fail")
    except LLMProviderError:
        pass

    logs = repo.list_for_task("task-fail")
    assert len(logs) == 1
    assert logs[0].success is False
    assert logs[0].error_message is not None


def test_no_usage_logging_without_a_repo() -> None:
    """LLMService must work fine with usage_log_repo=None (the default) — no crash, just no logging."""
    backend = FakeLLMBackend()
    service = LLMService(backend)
    response = service.generate([LLMMessage(role="user", content="hi")])
    assert response.content
