"""
Database models for the coordination bot - v2.
Aligned with Coordination Engine PRD: From Coordination Tool to Shared Experience Engine.
"""
from datetime import datetime
from typing import Any
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, JSON, Text,
    ForeignKey, CheckConstraint, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base: Any = declarative_base()


class User(Base):
    """Users table - global identity across groups."""
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), unique=True)
    display_name = Column(String(255))
    reputation = Column(Float, default=1.0)
    expertise_per_activity = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    constraints = relationship(
        "Constraint",
        back_populates="user",
        foreign_keys="[Constraint.user_id]"
    )
    target_constraints = relationship(
        "Constraint",
        back_populates="target_user",
        foreign_keys="[Constraint.target_user_id]"
    )
    logs = relationship("Log", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")
    reputation_records = relationship("Reputation", back_populates="user")
    early_feedback_given = relationship(
        "EarlyFeedback",
        back_populates="source_user",
        foreign_keys="[EarlyFeedback.source_user_id]",
    )
    early_feedback_received = relationship(
        "EarlyFeedback",
        back_populates="target_user",
        foreign_keys="[EarlyFeedback.target_user_id]",
    )
    preferences = relationship("UserPreference", back_populates="user", uselist=False)


class Group(Base):
    """Groups table - Telegram group context."""
    __tablename__ = "groups"
    
    group_id = Column(Integer, primary_key=True)
    telegram_group_id = Column(BigInteger, unique=True, nullable=False)
    group_name = Column(String(255))
    group_type = Column(String(50), default="casual")
    member_list = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    events = relationship("Event", back_populates="group")


class Event(Base):
    """Events table - gathering lifecycle."""
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True)
    group_id = Column(
        Integer,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False
    )
    event_type = Column(String(100), nullable=False)
    description = Column(Text)
    organizer_telegram_user_id = Column(BigInteger)
    admin_telegram_user_id = Column(BigInteger)
    scheduled_time = Column(DateTime)
    commit_by = Column(DateTime)
    duration_minutes = Column(Integer, default=120)
    threshold_attendance = Column(Integer, default=0)
    
    # PRD v2: Explicit threshold fields (Section 2.1)
    min_participants = Column(Integer, default=2)  # Absolute floor for viability
    target_participants = Column(Integer, default=6)  # Desired count for optimal experience
    collapse_at = Column(DateTime)  # Auto-cancel deadline for underthreshold events
    lock_deadline = Column(DateTime)  # Cutoff for attendance changes
    
    attendance_list = Column(JSON, default=list)  # DEPRECATED: kept for migration
    planning_prefs = Column(JSON, default=dict)
    ai_score = Column(Float, default=0.0)
    state = Column(String(20), default="proposed")
    created_at = Column(DateTime, default=datetime.utcnow)
    locked_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # PRD v2: Optimistic concurrency control (Priority 1)
    version = Column(Integer, default=0, nullable=False)

    group = relationship("Group", back_populates="events")
    constraints = relationship(
        "Constraint",
        back_populates="event",
        cascade="all, delete-orphan"
    )
    logs = relationship("Log", back_populates="event")
    feedback = relationship(
        "Feedback",
        back_populates="event",
        cascade="all, delete-orphan"
    )
    early_feedback = relationship(
        "EarlyFeedback",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    ailog = relationship("AILog", back_populates="event")
    # PRD v2: Normalized participants table (Priority 1)
    participants = relationship(
        "EventParticipant",
        back_populates="event",
        cascade="all, delete-orphan"
    )
    # PRD v2: Memory layer (Priority 3)
    memories = relationship(
        "EventMemory",
        back_populates="event",
        cascade="all, delete-orphan",
        uselist=False
    )


class UserPreference(Base):
    """User preferences table - private preference profiles."""
    __tablename__ = "user_preferences"
    
    preference_id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    time_preference = Column(String(50), default="any")
    activity_preference = Column(String(100), default="any")
    budget_preference = Column(String(50), default="any")
    location_type_preference = Column(String(100), default="any")
    transport_preference = Column(String(50), default="any")
    privacy_settings = Column(JSON, default=dict)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="preferences")


class Constraint(Base):
    """Constraints table - conditional participation."""
    __tablename__ = "constraints"
    
    constraint_id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    target_user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL")
    )
    event_id = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False
    )
    type = Column(String(50), nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship(
        "User",
        back_populates="constraints",
        foreign_keys=[user_id]
    )
    target_user = relationship(
        "User",
        back_populates="target_constraints",
        foreign_keys=[target_user_id]
    )
    event = relationship("Event", back_populates="constraints")


class Reputation(Base):
    """Reputation table - activity-specific credibility."""
    __tablename__ = "reputation"
    
    reputation_id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    activity_type = Column(String(100), nullable=False)
    score = Column(Float, default=1.0)
    decay_rate = Column(Float, default=0.05)
    last_updated = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "score >= 0 AND score <= 5",
            name="reputation_score_range"
        ),
        CheckConstraint(
            "decay_rate >= 0 AND decay_rate <= 1",
            name="reputation_decay_range"
        ),
        UniqueConstraint("user_id", "activity_type", name="uq_user_activity"),
    )
    
    user = relationship("User", back_populates="reputation_records")


class Log(Base):
    """Logs table - audit trail."""
    __tablename__ = "logs"
    
    log_id = Column(Integer, primary_key=True)
    event_id = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="SET NULL")
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL")
    )
    action = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_dict = Column("metadata", JSON, default=dict)
    
    event = relationship("Event", back_populates="logs")
    user = relationship("User", back_populates="logs")


class Feedback(Base):
    """Feedback table - post-event ratings."""
    __tablename__ = "feedback"
    
    feedback_id = Column(Integer, primary_key=True)
    event_id = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    score_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    comment = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(
            "value >= 0 AND value <= 5",
            name="feedback_value_range"
        ),
        UniqueConstraint(
            "event_id",
            "user_id",
            "score_type",
            name="uq_feedback_user_event"
        ),
    )
    
    event = relationship("Event", back_populates="feedback")
    user = relationship("User", back_populates="feedback")


class EarlyFeedback(Base):
    """Pre-event behavioral feedback signals for analytics and reputation."""
    __tablename__ = "early_feedback"

    early_feedback_id = Column(Integer, primary_key=True)
    event_id = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL")
    )
    target_user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = Column(String(50), nullable=False)
    signal_type = Column(String(50), nullable=False, default="overall")
    value = Column(Float, nullable=False)
    weight = Column(Float, default=0.5)
    confidence = Column(Float, default=0.6)
    sanitized_comment = Column(Text)
    is_private = Column(Integer, default=0)
    metadata_dict = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('constraint', 'discussion', 'private_peer', 'system')",
            name="early_feedback_source_type",
        ),
        CheckConstraint(
            "signal_type IN ('overall', 'reliability', 'cooperation', 'toxicity', 'commitment', 'trust')",
            name="early_feedback_signal_type",
        ),
        CheckConstraint("value >= 0 AND value <= 5", name="early_feedback_value_range"),
        CheckConstraint("weight >= 0 AND weight <= 1", name="early_feedback_weight_range"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="early_feedback_confidence_range"),
    )

    event = relationship("Event", back_populates="early_feedback")
    source_user = relationship(
        "User",
        back_populates="early_feedback_given",
        foreign_keys=[source_user_id],
    )
    target_user = relationship(
        "User",
        back_populates="early_feedback_received",
        foreign_keys=[target_user_id],
    )


class AILog(Base):
    """AILog table - AI decision tracking."""
    __tablename__ = "ailog"

    ailog_id = Column(Integer, primary_key=True)
    event_id = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="SET NULL")
    )
    recommendation_type = Column(String(100), nullable=False)
    recommendation_value = Column(Text, nullable=False)
    confidence = Column(Float)
    is_fallback = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="ailog")


# ============================================================================
# PRD v2: New Tables for Priority 1 - Structural Foundations
# ============================================================================

class ParticipantStatus(enum.Enum):
    """Participant status enum."""
    joined = "joined"
    confirmed = "confirmed"
    cancelled = "cancelled"
    no_show = "no_show"


class ParticipantRole(enum.Enum):
    """Participant role enum."""
    organizer = "organizer"
    participant = "participant"
    observer = "observer"


class EventParticipant(Base):
    """
    EventParticipant table - Normalized participation tracking.
    PRD v2 Section 2.1: Replaces attendance_list JSON column.
    """
    __tablename__ = "event_participants"

    event_id = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
    telegram_user_id = Column(
        BigInteger,
        primary_key=True,
        nullable=False
    )
    status = Column(
        SQLEnum(ParticipantStatus),
        default=ParticipantStatus.joined,
        nullable=False
    )
    role = Column(
        SQLEnum(ParticipantRole),
        default=ParticipantRole.participant,
        nullable=False
    )
    joined_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    source = Column(String(50))  # slash, callback, mention, dm
    
    event = relationship("Event", back_populates="participants")


class IdempotencyKey(Base):
    """
    IdempotencyKey table - Prevents duplicate command execution.
    PRD v2 Priority 1: Idempotent Command Execution.
    """
    __tablename__ = "idempotency_keys"

    idempotency_key = Column(String(255), primary_key=True)
    command_type = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    event_id = Column(Integer, ForeignKey("events.event_id"))
    status = Column(String(50), default="pending")  # pending, completed, failed
    response_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=False)
    
    user = relationship("User")
    event = relationship("Event")


class EventStateTransition(Base):
    """
    EventStateTransition table - Audit trail for state changes.
    PRD v2 Section 2.1: Each transition records actor, timestamp, reason, source.
    """
    __tablename__ = "event_state_transitions"

    transition_id = Column(Integer, primary_key=True)
    event_id = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False
    )
    from_state = Column(String(20), nullable=False)
    to_state = Column(String(20), nullable=False)
    actor_telegram_user_id = Column(BigInteger)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    reason = Column(Text)
    source = Column(String(50), nullable=False)  # slash, callback, AI mention
    
    event = relationship("Event")


# ============================================================================
# PRD v2: New Tables for Priority 3 - Layer 3 Memory
# ============================================================================

class EventMemory(Base):
    """
    EventMemory table - Memory Weave storage.
    PRD v2 Section 2.3: Makes events mean something through shared narratives.
    """
    __tablename__ = "event_memories"

    memory_id = Column(Integer, primary_key=True)
    event_id = Column(
        Integer,
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    fragments = Column(JSON, default=list)
    # Each fragment: {text, contributor_hash, tone_tag, submitted_at}
    hashtags = Column(JSON, default=list)  # 1-3 natural language tags
    outcome_markers = Column(JSON, default=list)  # follow-on events, collaborations
    weave_text = Column(Text)  # Bot-generated weave posted to group
    lineage_event_ids = Column(JSON, default=list)  # References to prior similar events
    tone_palette = Column(JSON, default=list)  # Coexisting tones identified
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    event = relationship("Event", back_populates="memories")
