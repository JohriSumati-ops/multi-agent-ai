"""
orchestration/message_bus.py — THE MESSAGE BUS

WHY THIS FILE EXISTS
---------------------
Per this phase's explicit requirement: "Agents must communicate ONLY
through messages. Never call another agent directly." Concretely, in a
single-process system, this means: no agent instance ever holds a
reference to another agent instance, and no orchestration component
(`WorkflowEngine`, `ExecutionStateManager`, `EventLogger`) is *directly
called* by another — they publish and subscribe to messages instead. The
`WorkflowEngine` publishes `TASK_STARTED`/`TASK_COMPLETED`/`TASK_FAILED`/
`PROGRESS` messages as it drives execution; `ExecutionStateManager` and
`EventLogger` each subscribe independently, with zero awareness of each
other or of the engine's internals beyond the message shape.

WHY THIS IS NOT A SINGLETON
--------------------------------
Unlike `AgentRegistry` (shared, process-wide, built once), a `MessageBus`
is scoped to ONE plan execution — constructed fresh per
`SupervisorAgent`/`WorkflowEngine` invocation, exactly like
`memory/working_memory.py::WorkingMemory`'s "gone after one request"
design. Message correlation (which messages belong to which execution) is
free this way: every message on a given bus instance belongs to that one
execution, with no need for a correlation ID to filter cross-request noise
out of subscriber callbacks.

WHY THIS IS NOT A REAL DISTRIBUTED MESSAGE QUEUE
-----------------------------------------------------
This project runs as a single FastAPI process with classical/DL agents,
not a distributed system with independently deployed agent workers —
introducing a real broker (Redis Pub/Sub, RabbitMQ, Kafka) here would be
architecture no current requirement justifies (see Phase 0's "don't
redesign the architecture" instruction extended to "don't over-engineer
new architecture either"). This in-process, thread-safe pub/sub
implementation gives the *decoupling* benefit message passing is meant to
provide, at the complexity level this phase's actual scale calls for. The
`MessageBus` interface itself doesn't preclude swapping in a real broker
later — every publish/subscribe call site would be unaffected.
"""

from __future__ import annotations

import enum
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


class MessageType(str, enum.Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    EVENT = "event"
    FAILURE = "failure"
    COMPLETION = "completion"
    PROGRESS = "progress"


@dataclass
class Message:
    type: MessageType
    topic: str  # e.g., "task.started", "task.completed" — subscribers filter on this
    payload: dict[str, Any] = field(default_factory=dict)
    sender: str | None = None
    correlation_id: str | None = None  # typically a task_id or plan_id
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    published_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


MessageHandler = Callable[[Message], None]


class MessageBus:
    """
    In-process, thread-safe publish/subscribe bus, scoped to one
    execution (see module docstring for why it's not a singleton).
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[MessageHandler]] = {}
        self._wildcard_subscribers: list[MessageHandler] = []
        self._history: list[Message] = []
        self._lock = threading.Lock()

    def subscribe(self, topic: str, handler: MessageHandler) -> None:
        """Subscribe to an exact topic (e.g., "task.completed")."""
        with self._lock:
            self._subscribers.setdefault(topic, []).append(handler)

    def subscribe_all(self, handler: MessageHandler) -> None:
        """Subscribe to every message regardless of topic — used by EventLogger."""
        with self._lock:
            self._wildcard_subscribers.append(handler)

    def publish(self, message: Message) -> None:
        with self._lock:
            self._history.append(message)
            handlers = list(self._subscribers.get(message.topic, [])) + list(self._wildcard_subscribers)

        # Handlers are invoked OUTSIDE the lock so a slow/misbehaving
        # subscriber can't block other publishers — a real concern once
        # WorkflowEngine's thread pool publishes from multiple worker
        # threads concurrently (see orchestration/workflow_engine.py).
        for handler in handlers:
            try:
                handler(message)
            except Exception:  # noqa: BLE001 — one broken subscriber must never break publishing
                from core.logging import get_logger

                get_logger("agent").exception(
                    "MessageBus subscriber raised while handling topic '%s'", message.topic
                )

    def publish_event(
        self, topic: str, *, payload: dict | None = None, sender: str | None = None, correlation_id: str | None = None
    ) -> Message:
        """Convenience: build-and-publish in one call — the shape every WorkflowEngine call site uses."""
        message = Message(
            type=MessageType.EVENT,
            topic=topic,
            payload=payload or {},
            sender=sender,
            correlation_id=correlation_id,
        )
        self.publish(message)
        return message

    def history(self, *, topic: str | None = None, correlation_id: str | None = None) -> list[Message]:
        with self._lock:
            messages = list(self._history)
        if topic is not None:
            messages = [m for m in messages if m.topic == topic]
        if correlation_id is not None:
            messages = [m for m in messages if m.correlation_id == correlation_id]
        return messages
