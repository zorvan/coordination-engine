"""
Database models for the coordination bot.
"""
from datetime import datetime
from typing import Any
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, JSON, Text,
    ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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
    scheduled_time = Column(DateTime)
    commit_by = Column(DateTime)
    duration_minutes = Column(Integer, default=120)
    threshold_attendance = Column(Integer, default=0)
    attendance_list = Column(JSON, default=list)
    planning_prefs = Column(JSON, default=dict)
    ai_score = Column(Float, default=0.0)
    state = Column(String(20), default="proposed")
    created_at = Column(DateTime, default=datetime.utcnow)
    locked_at = Column(DateTime)
    completed_at = Column(DateTime)

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
