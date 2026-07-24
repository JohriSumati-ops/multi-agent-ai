"""
tests/test_message_bus.py
"""

from __future__ import annotations

from orchestration.message_bus import Message, MessageBus, MessageType


def test_publish_and_topic_subscription() -> None:
    bus = MessageBus()
    received = []
    bus.subscribe("task.completed", lambda m: received.append(m))

    bus.publish_event("task.completed", payload={"task_id": "t1"})
    bus.publish_event("task.started", payload={"task_id": "t1"})  # different topic — should not be received

    assert len(received) == 1
    assert received[0].topic == "task.completed"


def test_wildcard_subscription_receives_every_message() -> None:
    bus = MessageBus()
    received = []
    bus.subscribe_all(lambda m: received.append(m))

    bus.publish_event("task.started")
    bus.publish_event("task.completed")

    assert len(received) == 2


def test_history_records_every_published_message() -> None:
    bus = MessageBus()
    bus.publish_event("a")
    bus.publish_event("b")
    assert len(bus.history()) == 2


def test_history_filters_by_topic() -> None:
    bus = MessageBus()
    bus.publish_event("task.started", payload={"task_id": "t1"})
    bus.publish_event("task.completed", payload={"task_id": "t1"})
    assert len(bus.history(topic="task.started")) == 1


def test_history_filters_by_correlation_id() -> None:
    bus = MessageBus()
    bus.publish_event("event", correlation_id="plan1")
    bus.publish_event("event", correlation_id="plan2")
    assert len(bus.history(correlation_id="plan1")) == 1


def test_a_broken_subscriber_does_not_prevent_other_subscribers_from_running() -> None:
    bus = MessageBus()
    received = []

    def broken_handler(message: Message) -> None:
        raise RuntimeError("subscriber exploded")

    bus.subscribe("event", broken_handler)
    bus.subscribe("event", lambda m: received.append(m))

    bus.publish_event("event")  # must not raise
    assert len(received) == 1


def test_message_has_a_unique_id_and_timestamp() -> None:
    m1 = Message(type=MessageType.EVENT, topic="a")
    m2 = Message(type=MessageType.EVENT, topic="a")
    assert m1.id != m2.id
    assert m1.published_at is not None


def test_publish_event_convenience_method_returns_the_message() -> None:
    bus = MessageBus()
    message = bus.publish_event("task.started", payload={"x": 1}, sender="engine")
    assert message.topic == "task.started"
    assert message.sender == "engine"
    assert message.payload == {"x": 1}
