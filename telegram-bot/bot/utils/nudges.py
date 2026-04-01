#!/usr/bin/env python3
"""
Nudges utility - Recognition-based framing for coordination.
PRD v2 Section 1.3: Recognition over Enforcement.

Design principles:
- No public shaming of cancellations
- No "low reliability" labels
- Frame as mutual dependence, not penalties
- Recognition framing: "people are counting on you" not "you're unreliable"
"""
import random
from typing import Optional


def generate_cancellation_notice(
    event_id: int,
    cancelled_user_name: str,
    event_type: str,
    remaining_count: int,
    is_organizer: bool = False,
) -> str:
    """
    Generate cancellation notice for organizer (PRIVATE).
    
    PRD Design constraint: No public shaming of cancellations.
    No "[X] cancelled" posts in group.
    """
    notices = [
        f"⚠️ {cancelled_user_name} had to drop from the {event_type}.\n"
        f"{remaining_count} people still in.",
        
        f"FYI: {cancelled_user_name} can't make it to the {event_type} anymore.\n"
        f"You still have {remaining_count} confirmed.",
        
        f"{cancelled_user_name} needed to cancel for the {event_type}.\n"
        f"{remaining_count} others are still coming.",
    ]
    
    return random.choice(notices)


def generate_fallback_notice(event_id: int, event_type: str) -> str:
    """Generate fallback notice when AI is unavailable."""
    return (
        f"ℹ️ AI scheduling is temporarily unavailable for the {event_type}.\n"
        f"Using standard scheduling rules. Everything else works normally!"
    )


def generate_personalized_reconfirmation(
    user_name: str,
    event_type: str,
    event_date: str,
    days_until: int,
) -> str:
    """
    Generate personalized reconfirmation request.
    
    PRD Design rule: No "you have a reliability penalty" messaging.
    Frame as "we want to make sure you can make it" not "you're unreliable".
    """
    if days_until <= 2:
        return (
            f"Hey {user_name}! 👋\n\n"
            f"The {event_type} is coming up ({event_date}).\n"
            f"Can you still make it? Just want to make sure!\n\n"
            f"Use /confirm {event_type.lower()} to let us know."
        )
    else:
        return (
            f"Hi {user_name}! Planning ahead for the {event_type} on {event_date}.\n\n"
            f"We're counting on you — can you confirm you'll be there?\n\n"
            f"Use /confirm {event_type.lower()} when you know."
        )


def generate_threshold_celebration(
    event_type: str,
    confirmed_count: int,
    target_count: int,
) -> str:
    """
    Generate celebration message when threshold is reached.
    
    This is a key materialization moment — the event becomes "real".
    """
    if confirmed_count >= target_count:
        return (
            f"✨ Awesome! We have enough for the {event_type}.\n"
            f"{confirmed_count} people in — it's happening!"
        )
    else:
        return (
            f"🎉 Great news! We have enough for the {event_type}.\n"
            f"{confirmed_count} people confirmed."
        )


def generate_mutual_dependence_reminder(
    user_name: str,
    event_type: str,
    other_participant_names: list[str],
) -> str:
    """
    Generate reminder showing who else is counting on the user.
    
    PRD Section 2.2.5: Visibility of mutual dependence.
    Not peer pressure — relational context.
    """
    if len(other_participant_names) == 1:
        other_str = other_participant_names[0]
    elif len(other_participant_names) == 2:
        other_str = f"{other_participant_names[0]} and {other_participant_names[1]}"
    else:
        other_str = f"{len(other_participant_names)} others"
    
    messages = [
        f"Hey {user_name}! Just a reminder:\n\n"
        f"{other_str} {('are' if len(other_participant_names) > 1 else 'is')} counting on you for the {event_type}.\n\n"
        f"Your presence matters!",
        
        f"Hi {user_name}!\n\n"
        f"The {event_type} won't be the same without you.\n"
        f"{other_str} {('are' if len(other_participant_names) > 1 else 'is')} already confirmed.",
    ]
    
    return random.choice(messages)


def generate_near_collapse_alert(
    event_type: str,
    needed_count: int,
    deadline_str: str,
) -> str:
    """
    Generate alert that event is at risk of collapse.
    
    PRD Section 2.2.1: Threshold fragility awareness without penalties.
    """
    messages = [
        f"⚠️ Heads up: the {event_type} needs {needed_count} more to stay alive.\n"
        f"Deadline: {deadline_str}\n\n"
        f"Can you or someone you know join?",
        
        f"The {event_type} is at risk!\n"
        f"We need {needed_count} more people by {deadline_str}.\n\n"
        f"Know someone who'd love this? Invite them!",
    ]
    
    return random.choice(messages)


def generate_reliability_trend_message(
    user_name: str,
    trend_direction: str,  # "up", "stable", "down"
    recent_events_count: int,
) -> str:
    """
    Generate personal reliability trend message (PRIVATE).
    
    PRD Section 2.2.4: Reputation as background signal, not score.
    No leaderboard, no score comparison — just personal trend.
    """
    if trend_direction == "up":
        return (
            f"📈 {user_name}, your reliability trend is looking great!\n\n"
            f"Over the last {recent_events_count} events, you've been consistently showing up.\n"
            f"This helps the group plan better events for everyone."
        )
    elif trend_direction == "stable":
        return (
            f"📊 {user_name}, your participation has been steady.\n\n"
            f"Thanks for being part of the last {recent_events_count} events!\n"
            f"Consistency helps the group thrive."
        )
    else:  # down
        return (
            f"📉 {user_name}, we've missed you at recent events.\n\n"
            f"Over the last {recent_events_count} planned events, you haven't been able to make it.\n"
            f"No worries — life happens! Just wanted you to know."
        )


def generate_post_event_thanks(
    event_type: str,
    participant_count: int,
    highlight: Optional[str] = None,
) -> str:
    """
    Generate post-event thanks message.
    
    Recognition framing: celebrate showing up, not just completing.
    """
    base_message = (
        f"✅ The {event_type} is complete!\n\n"
        f"Thanks to all {participant_count} who joined.\n"
        f"Showing up is what makes these events happen!"
    )
    
    if highlight:
        base_message += f"\n\n✨ Highlight: {highlight}"
    
    return base_message
