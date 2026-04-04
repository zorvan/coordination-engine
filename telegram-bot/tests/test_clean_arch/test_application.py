"""Tests for application layer — event bus, DTOs."""

from __future__ import annotations

import pytest
import asyncio

from coordination_engine.application.dto import (
    CreateEventCommand,
    Result,
)
from coordination_engine.application.event_bus import EventBus
from coordination_engine.domain.events import (
    DomainEvent,
    EventCreated,
    EventStateChanged,
)


class TestResult:
    def test_ok_with_data(self):
        result = Result.ok(data={"key": "value"})
        assert result.success
        assert result.data == {"key": "value"}
        assert result.errors == []

    def test_ok_with_messages(self):
        result = Result.ok(messages=["Success!"])
        assert result.success
        assert result.messages == ["Success!"]

    def test_fail_string(self):
        result = Result.fail("Something went wrong")
        assert not result.success
        assert result.errors == ["Something went wrong"]

    def test_fail_list(self):
        result = Result.fail(["Error 1", "Error 2"])
        assert not result.success
        assert result.errors == ["Error 1", "Error 2"]


class TestCreateEventCommand:
    def test_defaults(self):
        cmd = CreateEventCommand(
            group_telegram_id=1,
            organizer_telegram_id=2,
        )
        assert cmd.event_type == "social"
        assert cmd.duration_minutes == 120
        assert cmd.threshold_attendance == 3


class TestEventBus:
    @pytest.mark.asyncio
    async def test_publish_single_event(self):
        bus = EventBus()
        received = []

        async def handler(event: EventCreated) -> None:
            received.append(event)

        bus.subscribe(EventCreated, handler)
        event = EventCreated(
            event_id=1, organizer_telegram_user_id=2, group_id=3, description="Test"
        )
        await bus.publish(event)

        assert len(received) == 1
        assert received[0].event_id == 1

    @pytest.mark.asyncio
    async def test_publish_multiple_events(self):
        bus = EventBus()
        count = 0

        async def handler(event: EventCreated) -> None:
            nonlocal count
            count += 1

        bus.subscribe(EventCreated, handler)

        for i in range(3):
            await bus.publish(EventCreated(
                event_id=i, organizer_telegram_user_id=1, group_id=1, description=f"Event {i}"
            ))

        assert count == 3

    @pytest.mark.asyncio
    async def test_catch_all_handler(self):
        bus = EventBus()
        received = []

        async def catch_all(event: DomainEvent) -> None:
            received.append(event)

        bus.subscribe_all(catch_all)

        await bus.publish(EventCreated(event_id=1, organizer_telegram_user_id=2, group_id=3, description="Test"))
        await bus.publish(EventStateChanged(event_id=1, from_state="proposed", to_state="interested"))

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_handler_exception_logged(self):
        bus = EventBus()

        async def failing_handler(event: EventCreated) -> None:
            raise ValueError("Test error")

        bus.subscribe(EventCreated, failing_handler)

        # Should not raise — exceptions are caught and logged
        await bus.publish(EventCreated(event_id=1, organizer_telegram_user_id=2, group_id=3, description="Test"))

    @pytest.mark.asyncio
    async def test_publish_many(self):
        bus = EventBus()
        received = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        bus.subscribe_all(handler)

        events = [
            EventCreated(event_id=i, organizer_telegram_user_id=1, group_id=1, description=f"Event {i}")
            for i in range(3)
        ]
        await bus.publish_many(events)

        assert len(received) == 3
