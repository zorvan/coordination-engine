from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from db.models import ParticipantStatus
from tests.scenarios.simulator import EventScenarioSimulator


@pytest.mark.asyncio
async def test_scenario_simulator_supports_full_event_journey(db_session) -> None:
    simulator = EventScenarioSimulator(db_session)

    organizer = await simulator.create_user("ali", display_name="Ali", telegram_user_id=101)
    reza = await simulator.create_user("reza", display_name="Reza", telegram_user_id=102)
    sina = await simulator.create_user("sina", display_name="Sina", telegram_user_id=103)
    amir = await simulator.create_user("amir", display_name="Amir", telegram_user_id=104)
    mehdi = await simulator.create_user("mehdi", display_name="Mehdi", telegram_user_id=105)
    extra = await simulator.create_user("navid", display_name="Navid", telegram_user_id=106)

    group = await simulator.create_group(
        "FIFA Group",
        telegram_group_id=-1001,
        members=[organizer, reza, sina, amir, mehdi, extra],
    )
    event = await simulator.create_event(
        group=group,
        organizer=organizer,
        event_type="social",
        description="FIFA night at Amir's place",
        scheduled_time=datetime.utcnow() + timedelta(days=2),
        min_participants=3,
        target_participants=4,
        duration_minutes=180,
    )

    await simulator.join(event.event_id, organizer, role="organizer")
    await simulator.join(event.event_id, reza)
    event = await simulator.confirm(event.event_id, reza)
    assert event.state == "confirmed"

    await simulator.join(event.event_id, sina)
    await simulator.confirm(event.event_id, sina)
    await simulator.add_constraint(event.event_id, sina, amir, "if_joins")
    await simulator.add_availability(event.event_id, reza, "2026-04-09T19:00")

    await simulator.join(event.event_id, mehdi)
    await simulator.confirm(event.event_id, mehdi)
    await simulator.join(event.event_id, amir)
    await simulator.confirm(event.event_id, amir)

    position = await simulator.add_to_waitlist(event.event_id, extra)
    assert position == 1

    event = await simulator.modify_event(
        event.event_id,
        organizer,
        scheduled_time=datetime.utcnow() + timedelta(days=3),
        duration_minutes=150,
        target_participants=5,
    )
    assert event.state == "interested"

    participants = {int(p.telegram_user_id): p for p in await simulator.participant_rows(event.event_id)}
    assert participants[reza.telegram_user_id].status == ParticipantStatus.joined
    assert participants[sina.telegram_user_id].status == ParticipantStatus.joined

    await simulator.confirm(event.event_id, reza)
    await simulator.confirm(event.event_id, sina)
    await simulator.confirm(event.event_id, mehdi)
    await simulator.confirm(event.event_id, amir)
    event = await simulator.exit(event.event_id, amir)

    assert any(
        msg["chat_id"] == extra.telegram_user_id and "spot opened" in msg["text"].lower()
        for msg in simulator.bot.sent_messages
    )

    accepted = await simulator.accept_waitlist_offer(event.event_id, extra)
    assert accepted is True

    event = await simulator.lock(event.event_id, organizer)
    assert event.state == "locked"

    event = await simulator.complete_event(event.event_id, organizer)
    assert event.state == "completed"


@pytest.mark.asyncio
async def test_ultimate_chat_style_multi_attempts_build_failure_then_memory(db_session) -> None:
    simulator = EventScenarioSimulator(db_session)

    ali = await simulator.create_user("ali", display_name="Ali", telegram_user_id=201)
    reza = await simulator.create_user("reza", display_name="Reza", telegram_user_id=202)
    sina = await simulator.create_user("sina", display_name="Sina", telegram_user_id=203)
    mehdi = await simulator.create_user("mehdi", display_name="Mehdi", telegram_user_id=204)
    amir = await simulator.create_user("amir", display_name="Amir", telegram_user_id=205)

    group = await simulator.create_group(
        "Ultimate Test Group",
        telegram_group_id=-2001,
        members=[ali, reza, sina, mehdi, amir],
    )

    dropout_points = [2, 2, 1]
    for index, dropout in enumerate(dropout_points, start=1):
        event = await simulator.create_event(
            group=group,
            organizer=ali,
            event_type="social",
            description=f"FIFA attempt {index}",
            scheduled_time=datetime.utcnow() + timedelta(days=index),
            min_participants=3,
            target_participants=4,
            duration_minutes=180,
        )
        await simulator.join(event.event_id, ali, role="organizer")
        await simulator.join(event.event_id, reza)
        await simulator.confirm(event.event_id, reza)
        if dropout >= 2:
            await simulator.join(event.event_id, amir)
            await simulator.confirm(event.event_id, amir)
        await simulator.cancel_event(event.event_id, ali, reason="Too unstable to make it happen")

    pattern = await simulator.get_failure_pattern(group.group_id, "social")
    assert pattern is not None
    assert pattern["failed_count"] == 3
    assert pattern["last_dropout_point"] == 2

    final_event = await simulator.create_event(
        group=group,
        organizer=ali,
        event_type="social",
        description="Wednesday FIFA, 7 to 10, not too late",
        scheduled_time=datetime.utcnow() + timedelta(days=7),
        min_participants=3,
        target_participants=4,
        duration_minutes=180,
    )
    await simulator.join(final_event.event_id, ali, role="organizer")
    await simulator.join(final_event.event_id, reza)
    await simulator.join(final_event.event_id, mehdi)
    await simulator.join(final_event.event_id, amir)
    await simulator.confirm(final_event.event_id, reza)
    await simulator.confirm(final_event.event_id, mehdi)
    await simulator.confirm(final_event.event_id, amir)
    await simulator.lock(final_event.event_id, ali)
    await simulator.complete_event(final_event.event_id, ali)

    await simulator.record_memory_fragment(final_event.event_id, "Traffic was awful but once we started it clicked")
    hook = await simulator.get_memory_hook(group.group_id, "social")

    assert hook is not None
    assert "Traffic was awful" in hook


@pytest.mark.asyncio
async def test_modify_uncommit_and_reconfirm_are_modeled_in_simulator(db_session) -> None:
    simulator = EventScenarioSimulator(db_session)

    ali = await simulator.create_user("ali", display_name="Ali", telegram_user_id=301)
    reza = await simulator.create_user("reza", display_name="Reza", telegram_user_id=302)
    sina = await simulator.create_user("sina", display_name="Sina", telegram_user_id=303)

    group = await simulator.create_group(
        "Midweek Group",
        telegram_group_id=-3001,
        members=[ali, reza, sina],
    )
    event = await simulator.create_event(
        group=group,
        organizer=ali,
        event_type="social",
        description="FIFA after class",
        scheduled_time=datetime.utcnow() + timedelta(days=1),
        min_participants=2,
        target_participants=3,
        duration_minutes=120,
    )

    await simulator.join(event.event_id, ali, role="organizer")
    await simulator.join(event.event_id, reza)
    await simulator.join(event.event_id, sina)
    await simulator.confirm(event.event_id, reza)
    await simulator.confirm(event.event_id, sina)

    event = await simulator.modify_event(
        event.event_id,
        ali,
        scheduled_time=datetime.utcnow() + timedelta(days=2),
        description="FIFA after class, later start",
    )
    assert event.state == "interested"

    participants = {int(p.telegram_user_id): p for p in await simulator.participant_rows(event.event_id)}
    assert participants[reza.telegram_user_id].status == ParticipantStatus.joined
    assert participants[sina.telegram_user_id].status == ParticipantStatus.joined
    assert sum(1 for msg in simulator.bot.sent_messages if "modified" in msg["text"].lower()) >= 2

    await simulator.confirm(event.event_id, reza)
    event = await simulator.uncommit(event.event_id, reza)
    participants = {int(p.telegram_user_id): p for p in await simulator.participant_rows(event.event_id)}
    assert participants[reza.telegram_user_id].status == ParticipantStatus.joined
    assert event.state == "interested"

    event = await simulator.confirm(event.event_id, reza)
    assert event.state == "confirmed"


@pytest.mark.asyncio
async def test_waitlist_decline_rolls_forward_to_next_candidate(db_session) -> None:
    simulator = EventScenarioSimulator(db_session)

    ali = await simulator.create_user("ali", display_name="Ali", telegram_user_id=401)
    reza = await simulator.create_user("reza", display_name="Reza", telegram_user_id=402)
    mehdi = await simulator.create_user("mehdi", display_name="Mehdi", telegram_user_id=403)
    navid = await simulator.create_user("navid", display_name="Navid", telegram_user_id=404)
    omid = await simulator.create_user("omid", display_name="Omid", telegram_user_id=405)

    group = await simulator.create_group(
        "Waitlist Group",
        telegram_group_id=-4001,
        members=[ali, reza, mehdi, navid, omid],
    )
    event = await simulator.create_event(
        group=group,
        organizer=ali,
        event_type="social",
        description="Small apartment FIFA",
        scheduled_time=datetime.utcnow() + timedelta(days=1),
        min_participants=2,
        target_participants=3,
        duration_minutes=150,
    )

    await simulator.join(event.event_id, ali, role="organizer")
    await simulator.join(event.event_id, reza)
    await simulator.join(event.event_id, mehdi)
    await simulator.confirm(event.event_id, reza)
    await simulator.confirm(event.event_id, mehdi)

    assert await simulator.add_to_waitlist(event.event_id, navid) == 1
    assert await simulator.add_to_waitlist(event.event_id, omid) == 2

    await simulator.exit(event.event_id, mehdi)
    assert any(msg["chat_id"] == navid.telegram_user_id for msg in simulator.bot.sent_messages)

    declined = await simulator.decline_waitlist_offer(event.event_id, navid)
    assert declined is True
    assert any(msg["chat_id"] == omid.telegram_user_id for msg in simulator.bot.sent_messages)

    accepted = await simulator.accept_waitlist_offer(event.event_id, omid)
    assert accepted is True

    participants = {int(p.telegram_user_id): p for p in await simulator.participant_rows(event.event_id)}
    assert participants[omid.telegram_user_id].status == ParticipantStatus.confirmed
