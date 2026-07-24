"""
orchestration/event_logger.py — THE EVENT LOGGER

WHY THIS FILE EXISTS
---------------------
Persists a durable record of every orchestration event, subscribed to a
`MessageBus` instance exactly like `ExecutionStateManager`
(orchestration/state_manager.py) — an independent observer, not called
directly by the `WorkflowEngine`. The two subscribers exist for genuinely
different reasons: `ExecutionStateManager` answers "what is the CURRENT
state" (in-memory, ephemeral, gone when the request ends);
`EventLogger` answers "what HAPPENED, historically" (persisted to
`OrchestrationEvent` rows, queryable long after the request that produced
them has finished) — see docs/Phase5.md Section 12's frontend-timeline
rationale.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from models.orchestration_event import OrchestrationEvent
from orchestration.message_bus import Message, MessageBus
from repositories.orchestration_event_repository import OrchestrationEventRepository


class EventLogger:
    def __init__(self, db: Session, bus: MessageBus, *, plan_id: str, user_id: UUID | None = None) -> None:
        self.repo = OrchestrationEventRepository(db)
        self.plan_id = plan_id
        self.user_id = user_id
        bus.subscribe_all(self._handle_message)

    def _handle_message(self, message: Message) -> None:
        self.repo.create(
            OrchestrationEvent(
                plan_id=self.plan_id,
                task_id=message.payload.get("task_id"),
                user_id=self.user_id,
                event_type=message.type.value,
                topic=message.topic,
                payload=message.payload,
            )
        )

    def get_timeline(self) -> list[OrchestrationEvent]:
        return self.repo.list_for_plan(self.plan_id)
