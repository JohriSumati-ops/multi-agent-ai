"""
llm/llm_service.py — THE LLM SERVICE

WHY THIS FILE EXISTS
---------------------
No agent or reasoning-layer component calls a `BaseLLM` provider directly
— every call goes through this class, exactly the same discipline
`retrieval/embedder.py::EmbeddingService` established for embedding calls
in Phase 3. This is what adds, in one place: retry policy for transient
provider failures, a hard timeout per call, and running token-usage
accounting persisted via `LLMUsageLog` — none of which belong in
`ClaudeProvider` itself (see that file's docstring for why).

RETRY POLICY
----------------
Only `LLMProviderError` (network/API failures) is retried — a response
that came back successfully but failed structural validation
(`LLMResponseError`, raised one layer up by `ResponseValidator`) is NOT
retried here, because retrying an API call that already succeeded
mechanically wastes a call and money; a validation failure needs a
different remediation (a stricter prompt, a different model) that this
service has no way to apply automatically. This mirrors
`orchestration/workflow_engine.py`'s distinction between retryable and
non-retryable `TaskError`s from Phase 5.

TIMEOUT ENFORCEMENT
------------------------
Uses the exact same "soft timeout via a single-worker executor with
`shutdown(wait=False)`" pattern `orchestration/workflow_engine.py`
established in Phase 5 — see that file's docstring for why
`with ThreadPoolExecutor(...)` alone would silently defeat the timeout
(a real bug caught and fixed during Phase 5's own development).

TOKEN ACCOUNTING
--------------------
Every call — successful or not — writes one `LLMUsageLog` row (when a
database session is provided) via `LLMUsageLogRepository`, mirroring
`AgentExecutionLog`'s "one row per invocation" shape from Phase 1.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from uuid import UUID

from core.config import settings
from core.exceptions import LLMProviderError
from core.logging import get_logger
from llm.base_llm import BaseLLM, LLMMessage, LLMResponse

logger = get_logger("agent")

_RETRY_DELAY_SECONDS = 0.3


class LLMService:
    def __init__(
        self,
        backend: BaseLLM,
        *,
        max_retries: int | None = None,
        timeout_seconds: float | None = None,
        usage_log_repo=None,
        user_id: UUID | None = None,
    ) -> None:
        self.backend = backend
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.LLM_TIMEOUT_SECONDS
        self.usage_log_repo = usage_log_repo
        self.user_id = user_id

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        task_id: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generates a completion with retry + timeout applied, logging token
        usage regardless of outcome. Raises `LLMProviderError` if every
        retry attempt fails.
        """
        resolved_temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        resolved_max_tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

        attempt = 0
        last_error: Exception | None = None
        started = time.perf_counter()

        while attempt <= self.max_retries:
            attempt += 1
            try:
                response = self._call_with_timeout(messages, resolved_temperature, resolved_max_tokens, **kwargs)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                self._log_usage(response, elapsed_ms, task_id, success=True)
                return response
            except FutureTimeoutError:
                last_error = LLMProviderError(f"LLM call timed out after {self.timeout_seconds}s")
            except LLMProviderError as exc:
                last_error = exc

            if attempt <= self.max_retries:
                logger.warning("LLM call failed (attempt %d/%d): %s", attempt, self.max_retries + 1, last_error)
                time.sleep(_RETRY_DELAY_SECONDS)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self._log_usage(None, elapsed_ms, task_id, success=False, error=str(last_error))
        raise last_error

    def _call_with_timeout(
        self, messages: list[LLMMessage], temperature: float, max_tokens: int, **kwargs
    ) -> LLMResponse:
        """
        See module docstring's "Timeout Enforcement" — same pattern as
        orchestration/workflow_engine.py's `_invoke_agent`, deliberately
        NOT using `with ThreadPoolExecutor(...)` for the reason documented
        there.
        """
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self.backend.generate, messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
            return future.result(timeout=self.timeout_seconds)
        finally:
            executor.shutdown(wait=False)

    def _log_usage(
        self,
        response: LLMResponse | None,
        latency_ms: int,
        task_id: str | None,
        *,
        success: bool,
        error: str | None = None,
    ) -> None:
        if self.usage_log_repo is None:
            return

        from models.llm_usage_log import LLMUsageLog

        self.usage_log_repo.create(
            LLMUsageLog(
                task_id=task_id,
                user_id=self.user_id,
                provider=self.backend.provider_name,
                model_name=getattr(self.backend, "model_name", "unknown"),
                prompt_tokens=response.input_tokens if response else None,
                completion_tokens=response.output_tokens if response else None,
                latency_ms=latency_ms,
                success=success,
                error_message=error,
            )
        )
