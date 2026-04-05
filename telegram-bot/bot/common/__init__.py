"""Shared domain/presentation helpers for bot modules."""
from bot.common.attendance import (
    derive_state_from_attendance,
    has_attendee,
    has_confirmed,
    mark_joined,
    mark_confirmed,
    finalize_commitments,
    revert_confirmed_to_joined,
    remove_attendee,
    parse_attendance,
    parse_attendance_with_status,
)
from bot.common.confirmation import invalidate_confirmations_and_notify
from bot.common.deeplinks import build_start_link
from bot.common.event_access import attendance_telegram_ids, get_event_organizer_telegram_id, is_attendee
from bot.common.event_presenters import format_event_details_message, format_status_message
from bot.common.event_states import can_transition, EVENT_STATE_TRANSITIONS, STATE_EXPLANATIONS
from bot.common.scheduling import events_overlap, find_user_event_conflict
from bot.common.user_preferences import (
    get_user_preferences,
    create_or_update_user_preferences,
    delete_user_preferences,
    get_preference_value,
    merge_aggregate_preferences,
    get_preference_defaults,
    get_privacy_defaults,
    set_preference_private_mode,
    get_group_aggregate_preferences,
    refresh_expired_preferences,
    get_users_preferences,
)
from bot.common.rbac import (
    check_event_visibility_and_get_event,
    check_group_membership,
    check_can_lock_event,
    check_event_organizer,
    check_event_admin,
    check_event_participant,
    check_can_modify_event,
    check_can_submit_private_note,
    get_user_event_role,
)

__all__ = [
    # attendance
    "derive_state_from_attendance",
    "has_attendee",
    "has_confirmed",
    "mark_joined",
    "mark_confirmed",
    "finalize_commitments",
    "revert_confirmed_to_joined",
    "remove_attendee",
    "parse_attendance",
    "parse_attendance_with_status",
    # confirmation
    "invalidate_confirmations_and_notify",
    # deeplinks
    "build_start_link",
    # event access
    "attendance_telegram_ids",
    "get_event_organizer_telegram_id",
    "is_attendee",
    # presenters
    "format_event_details_message",
    "format_status_message",
    # states
    "can_transition",
    "EVENT_STATE_TRANSITIONS",
    "STATE_EXPLANATIONS",
    # scheduling
    "events_overlap",
    "find_user_event_conflict",
    # user preferences
    "get_user_preferences",
    "create_or_update_user_preferences",
    "delete_user_preferences",
    "get_preference_value",
    "merge_aggregate_preferences",
    "get_preference_defaults",
    "get_privacy_defaults",
    "set_preference_private_mode",
    "get_group_aggregate_preferences",
    "refresh_expired_preferences",
    "get_users_preferences",
    # rbac
    "check_event_visibility_and_get_event",
    "check_group_membership",
    "check_can_lock_event",
    "check_event_organizer",
    "check_event_admin",
    "check_event_participant",
    "check_can_modify_event",
    "check_can_submit_private_note",
    "get_user_event_role",
]
