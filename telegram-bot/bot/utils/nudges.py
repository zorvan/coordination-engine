#!/usr/bin/env python3
"""
Nudges utility - Recognition-based framing for coordination.
PRD v2 Section 1.3: Recognition over Enforcement.

Design principles:
- No public shaming of cancellations
- No "low reliability" labels or scores
- Frame as mutual dependence, not penalties
- Recognition framing: "people are counting on you" not "you're unreliable"
- Gravity over control: events feel real through visible momentum
- Bot as background orchestrator, not enforcer

This module replaces all penalty-based language with recognition-based framing.
"""
import random
from typing import Optional, List


# ============================================================================
# Cancellation Notices (PRIVATE to organizer only)
# ============================================================================

def generate_cancellation_notice(
    event_id: int,
    cancelled_user_name: str,
    event_type: str,
    remaining_count: int,
    is_organizer: bool = False,
    waitlist_count: int = 0,
) -> str:
    """
    Generate cancellation notice for organizer (PRIVATE).

    PRD Design constraint: No public shaming of cancellations.
    No "[X] cancelled" posts in group.

    Framing: Informational, not punitive. Focus on remaining group.
    """
    notices = [
        f"⚠️ {cancelled_user_name} had to drop from the {event_type}.\n"
        f"{remaining_count} people still in.",

        f"FYI: {cancelled_user_name} can't make it to the {event_type} anymore.\n"
        f"You still have {remaining_count} confirmed.",

        f"{cancelled_user_name} needed to cancel for the {event_type}.\n"
        f"{remaining_count} others are still coming.",
    ]

    message = random.choice(notices)

    # Add waitlist info if available (future feature)
    if waitlist_count > 0:
        message += f"\n\n📋 {waitlist_count} people on waitlist."

    return message


# ============================================================================
# Reconfirmation Requests (Personalized, Recognition-based)
# ============================================================================

def generate_personalized_reconfirmation(
    user_name: str,
    event_type: str,
    event_date: str,
    days_until: int,
    reliability_trend: Optional[str] = None,  # "good", "steady", "needs_attention"
) -> str:
    """
    Generate personalized reconfirmation request.

    PRD Design rule: No "you have a reliability penalty" messaging.
    Frame as "we want to make sure you can make it" not "you're unreliable".

    Args:
        user_name: User's display name
        event_type: Type of event
        event_date: Formatted date string
        days_until: Days until event
        reliability_trend: Optional trend indicator for personalization
    """
    # Base message - always recognition-based
    if days_until <= 2:
        base_messages = [
            f"Hey {user_name}! 👋\n\n"
            f"The {event_type} is coming up ({event_date}).\n"
            f"Can you still make it? Just want to make sure!\n\n"
            f"Use /confirm {event_type.lower()} to let us know.",

            f"Hi {user_name}! Quick check-in:\n\n"
            f"The {event_type} is in {days_until} days ({event_date}).\n"
            f"We're finalizing plans — can you confirm?\n\n"
            f"Tap /confirm {event_type.lower()} when you know!",
        ]
    else:
        base_messages = [
            f"Hi {user_name}! Planning ahead for the {event_type} on {event_date}.\n\n"
            f"We're counting on you — can you confirm you'll be there?\n\n"
            f"Use /confirm {event_type.lower()} when you know.",

            f"Hey {user_name}! The group is planning the {event_type}.\n\n"
            f"Your presence matters! Can you confirm for {event_date}?\n\n"
            f"Use /confirm {event_type.lower()} to let us know.",
        ]

    # Add recognition-based personalization if trend available
    # Note: Never mention "low reliability" or penalties
    if reliability_trend == "good":
        personalization = (
            "\n\n✨ You've been great at making it to recent events!\n"
            "Your consistency really helps the group plan better."
        )
    elif reliability_trend == "steady":
        personalization = (
            "\n\n🙏 Thanks for being part of this group!\n"
            "Every confirmation helps us create better experiences."
        )
    else:
        # Default - no trend mentioned, just warm framing
        personalization = ""

    message = random.choice(base_messages)
    if personalization:
        message += personalization

    return message


# ============================================================================
# Threshold & Celebration Messages
# ============================================================================

def generate_threshold_celebration(
    event_type: str,
    confirmed_count: int,
    target_count: int,
    participant_names: Optional[List[str]] = None,
) -> str:
    """
    Generate celebration message when threshold is reached.

    This is a key materialization moment — the event becomes "real".

    Framing: Collective achievement, not individual credit.
    """
    if confirmed_count >= target_count:
        base = (
            f"✨ Awesome! We have enough for the {event_type}.\n"
            f"{confirmed_count} people in — it's happening!"
        )
    else:
        base = (
            f"🎉 Great news! We have enough for the {event_type}.\n"
            f"{confirmed_count} people confirmed."
        )

    # Add participant names if available (builds social gravity)
    if participant_names and len(participant_names) > 0:
        names_str = ", ".join(participant_names[:5])  # Max 5 names
        if len(participant_names) > 5:
            names_str += f" and {len(participant_names) - 5} more"
        base += f"\n\nWho's in: {names_str}"

    return base


def generate_threshold_fragility_notice(
    event_type: str,
    confirmed_count: int,
    min_required: int,
    deadline_str: str,
) -> str:
    """
    Generate notice about threshold fragility.

    PRD Section 2.2.1: Threshold fragility awareness without penalties.

    Framing: Informational, not alarming. Focus on collective action.
    """
    needed = min_required - confirmed_count

    if needed == 1:
        messages = [
            f"⚠️ Heads up: the {event_type} needs just 1 more to stay alive.\n"
            f"Deadline: {deadline_str}\n\n"
            f"Know someone who'd love this? Invite them!",

            f"The {event_type} is on the edge!\n"
            f"We need 1 more person by {deadline_str}.\n\n"
            f"Can you think of anyone who'd enjoy this?",
        ]
    else:
        messages = [
            f"⚠️ Heads up: the {event_type} needs {needed} more to stay alive.\n"
            f"Deadline: {deadline_str}\n\n"
            f"Can you or someone you know join?",

            f"The {event_type} is at risk!\n"
            f"We need {needed} more people by {deadline_str}.\n\n"
            f"Know someone who'd love this? Invite them!",
        ]

    return random.choice(messages)


# ============================================================================
# Mutual Dependence Reminders
# ============================================================================

def generate_mutual_dependence_reminder(
    user_name: str,
    event_type: str,
    other_participant_names: List[str],
    user_status: str = "joined",  # "joined" or "confirmed"
) -> str:
    """
    Generate reminder showing who else is counting on the user.

    PRD Section 2.2.5: Visibility of mutual dependence.
    Not peer pressure — relational context.

    Framing: "Your presence matters" not "Don't let them down".
    """
    if len(other_participant_names) == 0:
        return f"Hey {user_name}! The {event_type} is coming up.\n\nYour presence matters!"

    if len(other_participant_names) == 1:
        other_str = other_participant_names[0]
        verb = "is"
    elif len(other_participant_names) == 2:
        other_str = f"{other_participant_names[0]} and {other_participant_names[1]}"
        verb = "are"
    else:
        other_str = f"{len(other_participant_names)} others"
        verb = "are"

    if user_status == "confirmed":
        messages = [
            f"Hey {user_name}! Just a reminder:\n\n"
            f"{other_str} {verb} counting on you for the {event_type}.\n\n"
            f"Your presence matters!",

            f"Hi {user_name}!\n\n"
            f"The {event_type} won't be the same without you.\n"
            f"{other_str} {verb} already confirmed.",
        ]
    else:  # joined but not confirmed
        messages = [
            f"Hey {user_name}! {other_str} {verb} confirmed for the {event_type}.\n\n"
            f"Can you confirm too? It helps everyone plan better!\n\n"
            f"Use /confirm to let the group know.",

            f"Hi {user_name}! The group is forming for the {event_type}.\n\n"
            f"{other_str} {verb} in — your confirmation would help solidify plans!\n\n"
            f"Use /confirm when you know.",
        ]

    return random.choice(messages)


# ============================================================================
# Near-Collapse Alerts
# ============================================================================

def generate_near_collapse_alert(
    event_type: str,
    needed_count: int,
    deadline_str: str,
    confirmed_names: Optional[List[str]] = None,
) -> str:
    """
    Generate alert that event is at risk of collapse.

    PRD Section 2.2.1: Threshold fragility awareness without penalties.

    Framing: Call to action, not doom. Focus on solution.
    """
    base_messages = [
        f"⚠️ Heads up: the {event_type} needs {needed_count} more to stay alive.\n"
        f"Deadline: {deadline_str}\n\n"
        f"Can you or someone you know join?",

        f"The {event_type} is at risk!\n"
        f"We need {needed_count} more people by {deadline_str}.\n\n"
        f"Know someone who'd love this? Invite them!",

        f"🚨 The {event_type} needs your help!\n"
        f"{needed_count} more people needed by {deadline_str}.\n\n"
        f"Every person counts — spread the word!",
    ]

    message = random.choice(base_messages)

    # Add confirmed names to show existing commitment (builds gravity)
    if confirmed_names and len(confirmed_names) > 0:
        names_str = ", ".join(confirmed_names[:3])
        if len(confirmed_names) > 3:
            names_str += f" and {len(confirmed_names) - 3} more"
        message += f"\n\nCurrently confirmed: {names_str}"

    return message


# ============================================================================
# Reliability Trend Messages (PRIVATE, Personal)
# ============================================================================

def generate_reliability_trend_message(
    user_name: str,
    trend_direction: str,  # "up", "stable", "down"
    recent_events_count: int,
    reliability_score: Optional[float] = None,
) -> str:
    """
    Generate personal reliability trend message (PRIVATE).

    PRD Section 2.2.4: Reputation as background signal, not score.
    No leaderboard, no score comparison — just personal trend.

    Framing: Supportive, not judgmental. Never shame.
    """
    if trend_direction == "up":
        return (
            f"📈 {user_name}, your reliability trend is looking great!\n\n"
            f"Over the last {recent_events_count} events, you've been consistently showing up.\n"
            f"This helps the group plan better events for everyone.\n\n"
            f"✨ Thank you for being someone the group can count on!"
        )

    elif trend_direction == "stable":
        return (
            f"📊 {user_name}, your participation has been steady.\n\n"
            f"Thanks for being part of the last {recent_events_count} events!\n"
            f"Consistency helps the group thrive.\n\n"
            f"🙏 Your presence matters!"
        )

    else:  # down - most sensitive, requires careful framing
        # NEVER use words like "unreliable", "problem", "concern", "warning"
        # Frame as "we've missed you" not "you've been absent"
        return (
            f"📉 {user_name}, we've missed you at recent events.\n\n"
            f"Over the last {recent_events_count} planned events, you haven't been able to make it.\n"
            f"No worries — life happens! Just wanted you to know.\n\n"
            f"💙 The group values your participation when you can make it!"
        )


# ============================================================================
# Post-Event Messages
# ============================================================================

def generate_post_event_thanks(
    event_type: str,
    participant_count: int,
    highlight: Optional[str] = None,
    memory_prompt: bool = True,
) -> str:
    """
    Generate post-event thanks message.

    Recognition framing: celebrate showing up, not just completing.

    Args:
        event_type: Type of event
        participant_count: Number of participants
        highlight: Optional highlight from the event
        memory_prompt: Whether to include memory collection prompt
    """
    base_message = (
        f"✅ The {event_type} is complete!\n\n"
        f"Thanks to all {participant_count} who joined.\n"
        f"Showing up is what makes these events happen!"
    )

    if highlight:
        base_message += f"\n\n✨ Highlight: {highlight}"

    if memory_prompt:
        base_message += (
            f"\n\n📿 Want to share a memory? "
            f"Use /remember {event_type.lower()} to add your fragment to the group's story."
        )

    return base_message


# ============================================================================
# General Nudges
# ============================================================================

def generate_participation_nudge(
    user_name: str,
    event_id: int,
    event_type: str,
    event_date: str,
    user_status: str = "not_joined",  # "not_joined", "joined", "confirmed"
) -> str:
    """
    Generate a nudge message for event participation.

    Framing: Invitation, not pressure. Focus on value, not obligation.

    Args:
        user_name: User's display name
        event_id: The event ID
        event_type: The type of event
        event_date: Formatted date string
        user_status: Current participation status
    """
    if user_status == "not_joined":
        messages = [
            f"Hey {user_name}! The {event_type} on {event_date} sounds fun.\n\n"
            f"Think you might enjoy it! Use /join {event_id} if you're in.",

            f"Hi {user_name}! The group is planning a {event_type}.\n\n"
            f"Your perspective would be valuable! /join {event_id}",
        ]
    elif user_status == "joined":
        messages = [
            f"Remember, the {event_type} is coming up ({event_date})!\n\n"
            f"Your participation matters to the group. "
            f"Use /confirm {event_id} to let everyone know you're in!",

            f"Hey! Just a reminder about the {event_type} on {event_date}.\n\n"
            f"We're counting on you! /confirm {event_id}",
        ]
    else:  # confirmed
        messages = [
            f"Excited for the {event_type} on {event_date}!\n\n"
            f"See you there, {user_name}! 🎉",

            f"The {event_type} is coming up and you're confirmed!\n\n"
            f"Looking forward to seeing you, {user_name}!",
        ]

    return random.choice(messages)


# ============================================================================
# Fallback & System Messages
# ============================================================================

def generate_fallback_notice(event_id: int, event_type: str) -> str:
    """Generate fallback notice when AI is unavailable."""
    return (
        f"ℹ️ AI scheduling is temporarily unavailable for the {event_type}.\n"
        f"Using standard scheduling rules. Everything else works normally!"
    )


def generate_system_notice(
    notice_type: str,
    event_id: int,
    details: Optional[str] = None,
) -> str:
    """
    Generate generic system notice.

    Framing: Informational, clear, non-alarming.
    """
    templates = {
        "lock": f"🔒 Event {event_id} is now locked.\n\nNo more changes can be made.",
        "unlock": f"🔓 Event {event_id} has been unlocked.\n\nChanges are now possible.",
        "cancel": f"❌ Event {event_id} has been cancelled.\n\nThank you for your interest.",
        "complete": f"✅ Event {event_id} is complete!\n\nThank you to all who participated.",
    }

    base = templates.get(notice_type, f"ℹ️ Event {event_id}: {details or 'Update available.'}")

    if details and details not in templates.values():
        base += f"\n\n{details}"

    return base


# ============================================================================
# Legacy/Compatibility Functions (for tests and backward compatibility)
# ============================================================================

def generate_nudge_message(
    event_id: int,
    user_id: int,
    event_type: str,
) -> str:
    """
    Generate a generic nudge message for event participation.

    Legacy function for backward compatibility.
    Use generate_participation_nudge for new code.

    Args:
        event_id: The event ID
        user_id: The user's Telegram ID
        event_type: Type of event

    Returns:
        A nudge message string
    """
    messages = [
        f"👋 Event {event_id} ({event_type}) is coming up!\n"
        f"User {user_id}, your participation matters!",

        f"📅 Reminder: Event {event_id} ({event_type}) needs you!\n"
        f"User {user_id}, join the group activity!",

        f"🎯 Event {event_id} for {event_type} - User {user_id}.\n"
        f"Your presence helps the group thrive!",
    ]
    return random.choice(messages)


def generate_fallback_warning(event_id: int) -> str:
    """
    Generate fallback notice when AI is unavailable.

    Legacy alias for generate_fallback_notice.
    """
    return generate_fallback_notice(event_id, "event")


def generate_reliability_warning(
    user_id: int,
    reliability_score: float,
) -> str:
    """
    Generate reliability trend message (PRIVATE).

    Legacy function - uses generate_reliability_trend_message internally.

    Args:
        user_id: User's Telegram ID
        reliability_score: Reliability score (0.0-1.0)

    Returns:
        A supportive message about reliability trends
    """
    if reliability_score >= 0.7:
        trend = "up"
    elif reliability_score >= 0.4:
        trend = "stable"
    else:
        trend = "down"

    return generate_reliability_trend_message(
        user_name=f"User {user_id}",
        trend_direction=trend,
        recent_events_count=5,
        reliability_score=reliability_score,
    )


def generate_deadline_warning(
    event_id: int,
    deadline_str: str,
) -> str:
    """
    Generate deadline reminder message.

    Args:
        event_id: The event ID
        deadline_str: Formatted deadline string

    Returns:
        A deadline reminder message
    """
    messages = [
        f"⏰ Event {event_id} deadline approaching!\n"
        f"Deadline: {deadline_str}\n\n"
        f"Don't miss out!",

        f"🕐 Heads up for event {event_id}!\n"
        f"Time remaining: {deadline_str}\n\n"
        f"Act now if you want to join!",

        f"⌛ Event {event_id} closes in {deadline_str}.\n\n"
        f"Join before it's too late!",
    ]
    return random.choice(messages)


def generate_lock_warning(event_id: int) -> str:
    """
    Generate event lock notice.

    Args:
        event_id: The event ID

    Returns:
        A lock notice message
    """
    return (
        f"🔒 Event {event_id} is now locked.\n\n"
        f"No more changes can be made. See you there!"
    )


def generate_threshold_warning(
    event_id: int,
    current_count: int,
    required_count: int,
) -> str:
    """
    Generate threshold warning message.

    Args:
        event_id: The event ID
        current_count: Current number of participants
        required_count: Required number of participants

    Returns:
        A threshold warning message
    """
    needed = required_count - current_count

    if needed > 0:
        messages = [
            f"⚠️ Event {event_id} is below threshold!\n"
            f"We have {current_count} of {required_count} needed.\n"
            f"{needed} more people needed to make it happen!",

            f"📊 Event {event_id} needs more participants!\n"
            f"Current: {current_count}/{required_count}\n"
            f"We need {needed} more to confirm!",
        ]
        return random.choice(messages)
    else:
        return (
            f"✅ Event {event_id} has reached threshold!\n"
            f"{current_count}/{required_count} - It's happening!"
        )
