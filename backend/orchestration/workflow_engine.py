"""
orchestration/workflow_engine.py — THE WORKFLOW ENGINE

WHY THIS FILE EXISTS
---------------------
The only component that actually calls `agent.run()`. Everything else in
this package (`PlanBuilder`, `AgentScheduler`, `ExecutionStateManager`)
decides or observes — this executes. See docs/Phase5.md Section 10 for
the full design; this docstring covers implementation specifics.

HOW ONE TASK BECOMES AN AGENT INVOCATION
----------------------------------------------
For each runnable task, the engine: (1) constructs a fresh
`core.agent_bus.TaskContext` (Phase 1) seeded from `Task.payload` — the
exact same mechanism `document_processing/pipeline.py` already uses to
hand data to an agent; (2) instantiates the agent class the
`AgentRegistry` resolved (never a call site elsewhere naming a concrete
class); (3) calls `agent.run(context)`, which returns Phase 1's
`AgentResult` — timing, confidence, and error information all come from
there, not reinvented here.

PARALLELISM
--------------
Tasks in the same scheduling "wave" (no dependency relationship among
them — see `AgentScheduler.get_runnable_tasks`) are submitted to a
`ThreadPoolExecutor` together. A thread pool (not a process pool) is the
right tool here: the agents that exist so far are I/O-adjacent (file
reads, a local model forward pass) rather than CPU-bound in a way that
would benefit from bypassing the GIL via separate processes, and a thread
pool avoids the serialization overhead a process pool would impose on
`TaskContext`/`AgentResult` objects.

RETRIES AND TIMEOUTS
-------------------------
Each task attempt runs under `concurrent.futures.Future.result(timeout=...)`
— a task that hangs past `Task.timeout_seconds` is treated as a failure
(not left to run forever) and is retried like any other failure, up to
`Task.max_retries`. Retry delay is a short fixed pause (not exponential
backoff) — see docs/Phase5.md Section 11 for why that's the appropriate
choice for this project's classical/DL agents.

FAILURE PROPAGATION AND PARTIAL COMPLETION
------------------------------------------------
After each wave, the engine asks `AgentScheduler.get_blocked_tasks()` for
tasks whose dependencies permanently failed, and marks them `SKIPPED`
(with a reason) rather than leaving them stuck — this is what turns "one
failure" into "one failure plus its direct dependents," not "the entire
plan." Every other independent branch keeps executing normally.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from agents.base_agent import BaseAgent
from core.agent_bus import TaskContext
from core.logging import get_logger
from orchestration.agent_registry import AgentRegistry
from orchestration.agent_scheduler import AgentScheduler
from orchestration.execution_plan import ExecutionPlan
from orchestration.message_bus import MessageBus
from orchestration.task import Task, TaskError, TaskResult, TaskStatus

logger = get_logger("agent")

_RETRY_DELAY_SECONDS = 0.2


class WorkflowEngine:
    def __init__(
        self,
        registry: AgentRegistry,
        bus: MessageBus,
        *,
        scheduler: AgentScheduler | None = None,
        max_workers: int = 4,
    ) -> None:
        self.registry = registry
        self.bus = bus
        self.scheduler = scheduler or AgentScheduler()
        self.max_workers = max_workers
        self._cancelled = False
        self._context_lock = threading.Lock()
        self._shared_context: TaskContext | None = None

    def cancel(self) -> None:
        self._cancelled = True

    def execute(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Drives `plan` to completion (every task reaches a terminal state),
        returning the same plan object with every task's final status/result
        populated. Never raises for a task-level failure — see module
        docstring's "Failure Propagation and Partial Completion."

        Uses ONE shared `TaskContext` for the entire plan (not one per
        task) — this is what lets a dependent task read the outputs its
        dependencies wrote into `intermediate_results`, exactly like
        `document_processing/pipeline.py` already relies on for the Phase
        2 agent chain. A bug where each task got its own fresh, isolated
        context (so `extract_metadata` could never see `parse_document`'s
        output) was caught here during initial testing — this shared
        context is the fix.
        """
        self._shared_context = TaskContext(original_query=plan.goal)
        self.bus.publish_event("plan.started", payload={"plan_id": plan.id, "goal": plan.goal})

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while not plan.is_complete():
                if self._cancelled:
                    self._cancel_remaining(plan)
                    break

                blocked = self.scheduler.get_blocked_tasks(plan.tasks)
                for task in blocked:
                    self._skip_task(task, "A dependency failed or was skipped")

                runnable = self.scheduler.get_runnable_tasks(plan.tasks)
                if not runnable:
                    if not plan.is_complete():
                        # No runnable tasks but the plan isn't complete either —
                        # every remaining task must be genuinely WAITING on
                        # something still in flight from a previous wave, or
                        # (defensively) the graph has an issue PlanBuilder's
                        # cycle check should have already caught. Break to
                        # avoid a silent infinite loop either way.
                        break
                    continue

                futures = {executor.submit(self._run_task_with_retries, task): task for task in runnable}
                for future in futures:
                    future.result()  # propagate any *engine-level* (not task-level) exception

        self.bus.publish_event(
            "plan.completed",
            payload={
                "plan_id": plan.id,
                "succeeded": len(plan.successful_tasks()),
                "failed": len(plan.failed_tasks()),
            },
        )
        return plan

    def _run_task_with_retries(self, task: Task) -> None:
        attempt = 0
        while True:
            attempt += 1
            task.mark_running()
            self.bus.publish_event(
                "task.started",
                payload={"task_id": task.id, "status": TaskStatus.RUNNING.value, "capability": task.capability},
            )

            try:
                agent_result = self._invoke_agent(task)
            except FutureTimeoutError:
                agent_result = None
                task_error = TaskError(message=f"Task timed out after {task.timeout_seconds}s", is_retryable=True)
            else:
                task_error = None

            if agent_result is not None and agent_result.success:
                result = TaskResult(
                    task_id=task.id,
                    success=True,
                    output=agent_result.output,
                    confidence=agent_result.confidence_score,
                    execution_time_ms=agent_result.execution_time_ms,
                    attempt_count=attempt,
                )
                task.mark_completed(result)
                self.bus.publish_event(
                    "task.completed",
                    payload={"task_id": task.id, "status": TaskStatus.COMPLETED.value, "capability": task.capability},
                )
                return

            # --- failure path ---
            if task_error is None:
                task_error = TaskError(
                    message=(agent_result.error_message if agent_result else "Unknown failure"),
                    error_code=(agent_result.error_code if agent_result else None),
                )

            if attempt <= task.max_retries and task_error.is_retryable:
                task.status = TaskStatus.RETRYING
                self.bus.publish_event(
                    "task.retrying",
                    payload={"task_id": task.id, "status": TaskStatus.RETRYING.value, "attempt": attempt},
                )
                time.sleep(_RETRY_DELAY_SECONDS)
                continue

            result = TaskResult(
                task_id=task.id,
                success=False,
                confidence=agent_result.confidence_score if agent_result else None,
                execution_time_ms=agent_result.execution_time_ms if agent_result else None,
                attempt_count=attempt,
                error=task_error,
            )
            task.mark_failed(result)
            self.bus.publish_event(
                "task.failed",
                payload={"task_id": task.id, "status": TaskStatus.FAILED.value, "error": task_error.message},
            )
            return

    def _invoke_agent(self, task: Task):
        """
        Runs the agent call under its own short-lived single-worker
        executor so `task.timeout_seconds` can be enforced with
        `Future.result(timeout=...)` and raise `FutureTimeoutError` back
        into `_run_task_with_retries`'s retry handling — Python threads
        can't be forcibly killed, so a timed-out call's underlying thread
        keeps running in the background until it naturally finishes; its
        result is simply discarded, which is the standard, accepted
        pattern for soft timeouts without true thread cancellation.

        Deliberately NOT using `with ThreadPoolExecutor(...) as executor:`
        here — that context manager calls `shutdown(wait=True)` on exit,
        which would block until the (possibly hung) thread finishes
        anyway, completely defeating the timeout. `shutdown(wait=False)`
        lets this method return as soon as `future.result()` does, while
        the background thread is left to finish (or hang) on its own —
        this was caught by re-reading this method's own docstring claim
        against what the code actually did, not by a failing test, which
        is exactly the kind of bug that's easy to ship if timeout paths
        aren't specifically exercised.
        """
        registration = self.registry.get(task.capability)
        agent: BaseAgent = registration.agent_class()

        # Merge this task's payload into the SHARED plan-level context
        # under lock — see execute()'s docstring for why one shared
        # context (not one per task) is required for dependent tasks to
        # see their dependencies' outputs. The lock protects against two
        # tasks in the same parallel wave both mutating
        # intermediate_results concurrently; independent tasks in a wave
        # never depend on each other's keys, so this is purely a
        # dict-corruption safeguard, not a correctness requirement between
        # same-wave tasks.
        with self._context_lock:
            self._shared_context.intermediate_results.update(task.payload)
            context = self._shared_context

        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(agent.run, context)
            return future.result(timeout=task.timeout_seconds)
        finally:
            executor.shutdown(wait=False)

    def _skip_task(self, task: Task, reason: str) -> None:
        task.mark_skipped(reason)
        self.bus.publish_event(
            "task.skipped",
            payload={"task_id": task.id, "status": TaskStatus.SKIPPED.value, "reason": reason},
        )

    def _cancel_remaining(self, plan: ExecutionPlan) -> None:
        for task in plan.tasks:
            if task.status in (TaskStatus.QUEUED, TaskStatus.WAITING):
                task.status = TaskStatus.CANCELLED
                task.result = TaskResult(
                    task_id=task.id, success=False, error=TaskError(message="Execution cancelled", is_retryable=False)
                )
                self.bus.publish_event(
                    "task.cancelled", payload={"task_id": task.id, "status": TaskStatus.CANCELLED.value}
                )
