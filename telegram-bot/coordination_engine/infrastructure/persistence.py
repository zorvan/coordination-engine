"""SQLAlchemy Unit of Work and repository implementations.

Maps between domain entities (coordination_engine.domain) and
existing ORM models (db.models).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import db.models as orm
from coordination_engine.domain.entities import (
    Constraint,
    Event,
    EventParticipant,
    Group,
    PlanningPreferences,
    StateTransition,
    User,
)
from coordination_engine.domain.exceptions import ConcurrencyError, EntityNotFoundError
from coordination_engine.domain.repositories import (
    IConstraintRepository,
    IEventRepository,
    IEventStore,
    IGroupRepository,
    IParticipantRepository,
    IStateTransitionRepository,
    IUserRepository,
)
from coordination_engine.domain.value_objects import (
    ConstraintType,
    EventState,
    EventType,
    ParticipantRole,
    ParticipantStatus,
)


# ---------------------------------------------------------------------------
# Mappers — ORM ↔ Domain
# ---------------------------------------------------------------------------

class EventMapper:
    """Bidirectional mapping between ORM Event and domain Event."""

    @staticmethod
    def to_domain(orm_event: orm.Event) -> Event:
        prefs: dict[str, str] = orm_event.planning_prefs or {}
        return Event(
            event_id=orm_event.event_id,
            group_id=orm_event.group_id,
            event_type=EventType(orm_event.event_type),
            description=orm_event.description or "",
            organizer_telegram_user_id=orm_event.organizer_telegram_user_id,
            admin_telegram_user_id=orm_event.admin_telegram_user_id,
            scheduled_time=orm_event.scheduled_time,
            commit_by=orm_event.commit_by,
            collapse_at=orm_event.collapse_at,
            lock_deadline=orm_event.lock_deadline,
            duration_minutes=orm_event.duration_minutes or 120,
            threshold_attendance=orm_event.threshold_attendance or 3,
            min_participants=orm_event.min_participants or 2,
            target_participants=orm_event.target_participants or 5,
            planning_prefs=PlanningPreferences.from_dict(prefs),
            ai_score=orm_event.ai_score,
            state=EventState(orm_event.state),
            version=orm_event.version or 0,
            locked_at=orm_event.locked_at,
            completed_at=orm_event.completed_at,
            created_at=orm_event.created_at,
        )

    @staticmethod
    def to_orm(domain_event: Event, existing: orm.Event | None = None) -> orm.Event:
        if existing:
            obj = existing
        else:
            obj = orm.Event()

        obj.event_type = domain_event.event_type.value
        obj.description = domain_event.description
        obj.organizer_telegram_user_id = domain_event.organizer_telegram_user_id
        obj.admin_telegram_user_id = domain_event.admin_telegram_user_id
        obj.scheduled_time = domain_event.scheduled_time
        obj.commit_by = domain_event.commit_by
        obj.collapse_at = domain_event.collapse_at
        obj.lock_deadline = domain_event.lock_deadline
        obj.duration_minutes = domain_event.duration_minutes
        obj.threshold_attendance = domain_event.threshold_attendance
        obj.min_participants = domain_event.min_participants
        obj.target_participants = domain_event.target_participants
        obj.planning_prefs = domain_event.planning_prefs.to_dict()
        obj.ai_score = domain_event.ai_score
        obj.state = domain_event.state.value
        obj.version = domain_event.version
        obj.locked_at = domain_event.locked_at
        obj.completed_at = domain_event.completed_at

        if domain_event.group_id is not None:
            obj.group_id = domain_event.group_id

        return obj


class ParticipantMapper:
    """Bidirectional mapping between ORM EventParticipant and domain EventParticipant."""

    @staticmethod
    def to_domain(orm_p: orm.EventParticipant) -> EventParticipant:
        return EventParticipant(
            event_id=orm_p.event_id,
            telegram_user_id=orm_p.telegram_user_id,
            status=ParticipantStatus(orm_p.status.value),
            role=ParticipantRole(orm_p.role.value),
            joined_at=orm_p.joined_at,
            confirmed_at=orm_p.confirmed_at,
            cancelled_at=orm_p.cancelled_at,
            source=orm_p.source,
        )

    @staticmethod
    def to_orm(domain_p: EventParticipant, existing: orm.EventParticipant | None = None) -> orm.EventParticipant:
        if existing:
            obj = existing
        else:
            obj = orm.EventParticipant()

        obj.event_id = domain_p.event_id
        obj.telegram_user_id = domain_p.telegram_user_id
        obj.status = orm.ParticipantStatus(domain_p.status.value)
        obj.role = orm.ParticipantRole(domain_p.role.value)
        obj.joined_at = domain_p.joined_at
        obj.confirmed_at = domain_p.confirmed_at
        obj.cancelled_at = domain_p.cancelled_at
        obj.source = domain_p.source

        return obj


class UserMapper:
    @staticmethod
    def to_domain(orm_user: orm.User) -> User:
        return User(
            user_id=orm_user.user_id,
            telegram_user_id=orm_user.telegram_user_id,
            username=orm_user.username,
            display_name=orm_user.display_name,
            reputation=orm_user.reputation or 1.0,
            expertise_per_activity=orm_user.expertise_per_activity or {},
        )

    @staticmethod
    def to_orm(domain_user: User, existing: orm.User | None = None) -> orm.User:
        if existing:
            obj = existing
        else:
            obj = orm.User()

        obj.telegram_user_id = domain_user.telegram_user_id
        obj.username = domain_user.username
        obj.display_name = domain_user.display_name
        obj.reputation = domain_user.reputation
        obj.expertise_per_activity = domain_user.expertise_per_activity

        return obj


class GroupMapper:
    @staticmethod
    def to_domain(orm_group: orm.Group) -> Group:
        return Group(
            group_id=orm_group.group_id,
            telegram_group_id=orm_group.telegram_group_id,
            group_name=orm_group.group_name,
            group_type=orm_group.group_type or "group",
            member_list=orm_group.member_list or [],
        )

    @staticmethod
    def to_orm(domain_group: Group, existing: orm.Group | None = None) -> orm.Group:
        if existing:
            obj = existing
        else:
            obj = orm.Group()

        obj.telegram_group_id = domain_group.telegram_group_id
        obj.group_name = domain_group.group_name
        obj.group_type = domain_group.group_type
        obj.member_list = domain_group.member_list

        return obj


class ConstraintMapper:
    @staticmethod
    def to_domain(orm_c: orm.Constraint) -> Constraint:
        return Constraint(
            constraint_id=orm_c.constraint_id,
            user_id=orm_c.user_id,
            target_user_id=orm_c.target_user_id,
            event_id=orm_c.event_id,
            type=ConstraintType(orm_c.type),
            confidence=orm_c.confidence or 1.0,
            created_at=orm_c.created_at,
        )

    @staticmethod
    def to_orm(domain_c: Constraint, existing: orm.Constraint | None = None) -> orm.Constraint:
        if existing:
            obj = existing
        else:
            obj = orm.Constraint()

        obj.user_id = domain_c.user_id
        obj.target_user_id = domain_c.target_user_id
        obj.event_id = domain_c.event_id
        obj.type = domain_c.type.value
        obj.confidence = domain_c.confidence

        return obj


class StateTransitionMapper:
    @staticmethod
    def to_domain(orm_st: orm.EventStateTransition) -> StateTransition:
        return StateTransition(
            event_id=orm_st.event_id,
            from_state=EventState(orm_st.from_state),
            to_state=EventState(orm_st.to_state),
            actor_telegram_user_id=orm_st.actor_telegram_user_id,
            timestamp=orm_st.timestamp,
            reason=orm_st.reason or "",
            source=orm_st.source,
        )

    @staticmethod
    def to_orm(domain_st: StateTransition) -> orm.EventStateTransition:
        return orm.EventStateTransition(
            event_id=domain_st.event_id,
            from_state=domain_st.from_state.value,
            to_state=domain_st.to_state.value,
            actor_telegram_user_id=domain_st.actor_telegram_user_id,
            timestamp=domain_st.timestamp or datetime.utcnow(),
            reason=domain_st.reason,
            source=domain_st.source,
        )


# ---------------------------------------------------------------------------
# Repository Implementations
# ---------------------------------------------------------------------------

class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def by_id(self, user_id: int) -> Optional[User]:
        result = await self._session.execute(
            select(orm.User).where(orm.User.user_id == user_id)
        )
        orm_user = result.scalar_one_or_none()
        return UserMapper.to_domain(orm_user) if orm_user else None

    async def by_telegram_id(self, telegram_user_id: int) -> Optional[User]:
        result = await self._session.execute(
            select(orm.User).where(orm.User.telegram_user_id == telegram_user_id)
        )
        orm_user = result.scalar_one_or_none()
        return UserMapper.to_domain(orm_user) if orm_user else None

    async def by_username(self, username: str) -> Optional[User]:
        result = await self._session.execute(
            select(orm.User).where(orm.User.username == username.lstrip("@").lower())
        )
        orm_user = result.scalar_one_or_none()
        return UserMapper.to_domain(orm_user) if orm_user else None

    async def save(self, user: User) -> User:
        existing = None
        if user.user_id:
            result = await self._session.execute(
                select(orm.User).where(orm.User.user_id == user.user_id)
            )
            existing = result.scalar_one_or_none()
        elif user.telegram_user_id:
            result = await self._session.execute(
                select(orm.User).where(orm.User.telegram_user_id == user.telegram_user_id)
            )
            existing = result.scalar_one_or_none()

        orm_user = UserMapper.to_orm(user, existing)
        if not existing:
            self._session.add(orm_user)
        await self._session.flush()
        await self._session.refresh(orm_user)
        return UserMapper.to_domain(orm_user)

    async def get_or_create_by_telegram(
        self,
        telegram_user_id: int,
        *,
        username: str | None = None,
        display_name: str | None = None,
    ) -> User:
        result = await self._session.execute(
            select(orm.User).where(orm.User.telegram_user_id == telegram_user_id)
        )
        orm_user = result.scalar_one_or_none()

        if orm_user:
            domain_user = UserMapper.to_domain(orm_user)
        else:
            domain_user = User(
                telegram_user_id=telegram_user_id,
                username=username,
                display_name=display_name,
            )
            orm_user = UserMapper.to_orm(domain_user)
            self._session.add(orm_user)
            await self._session.flush()
            await self._session.refresh(orm_user)
            domain_user = UserMapper.to_domain(orm_user)

        # Update display info if provided
        updated = False
        if username and not domain_user.username:
            domain_user.username = username
            updated = True
        if display_name and not domain_user.display_name:
            domain_user.display_name = display_name
            updated = True

        if updated:
            UserMapper.to_orm(domain_user, orm_user)
            await self._session.flush()
            await self._session.refresh(orm_user)
            domain_user = UserMapper.to_domain(orm_user)

        return domain_user


class SQLAlchemyGroupRepository(IGroupRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def by_id(self, group_id: int) -> Optional[Group]:
        result = await self._session.execute(
            select(orm.Group).where(orm.Group.group_id == group_id)
        )
        orm_group = result.scalar_one_or_none()
        return GroupMapper.to_domain(orm_group) if orm_group else None

    async def by_telegram_id(self, telegram_group_id: int) -> Optional[Group]:
        result = await self._session.execute(
            select(orm.Group).where(orm.Group.telegram_group_id == telegram_group_id)
        )
        orm_group = result.scalar_one_or_none()
        return GroupMapper.to_domain(orm_group) if orm_group else None

    async def save(self, group: Group) -> Group:
        existing = None
        if group.group_id:
            result = await self._session.execute(
                select(orm.Group).where(orm.Group.group_id == group.group_id)
            )
            existing = result.scalar_one_or_none()

        orm_group = GroupMapper.to_orm(group, existing)
        if not existing:
            self._session.add(orm_group)
        await self._session.flush()
        await self._session.refresh(orm_group)
        return GroupMapper.to_domain(orm_group)

    async def ensure_exists(
        self,
        telegram_group_id: int,
        *,
        group_name: str | None = None,
    ) -> Group:
        result = await self._session.execute(
            select(orm.Group).where(orm.Group.telegram_group_id == telegram_group_id)
        )
        orm_group = result.scalar_one_or_none()

        if orm_group:
            return GroupMapper.to_domain(orm_group)

        domain_group = Group(
            telegram_group_id=telegram_group_id,
            group_name=group_name,
        )
        orm_group = GroupMapper.to_orm(domain_group)
        self._session.add(orm_group)
        await self._session.flush()
        await self._session.refresh(orm_group)
        return GroupMapper.to_domain(orm_group)


class SQLAlchemyEventRepository(IEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def by_id(self, event_id: int) -> Optional[Event]:
        result = await self._session.execute(
            select(orm.Event).where(orm.Event.event_id == event_id)
        )
        orm_event = result.scalar_one_or_none()
        return EventMapper.to_domain(orm_event) if orm_event else None

    async def active_for_group(self, group_id: int) -> list[Event]:
        result = await self._session.execute(
            select(orm.Event).where(
                orm.Event.group_id == group_id,
                orm.Event.state.in_(["proposed", "interested", "confirmed", "locked"]),
            ).order_by(orm.Event.created_at.desc())
        )
        return [EventMapper.to_domain(e) for e in result.scalars().all()]

    async def active_for_user(self, telegram_user_id: int) -> list[Event]:
        subq = (
            select(orm.EventParticipant.event_id)
            .where(
                orm.EventParticipant.telegram_user_id == telegram_user_id,
                orm.EventParticipant.status.in_(["joined", "confirmed"]),
            )
            .scalar_subquery()
        )
        result = await self._session.execute(
            select(orm.Event).where(
                orm.Event.event_id.in_(subq),
                orm.Event.state.in_(["proposed", "interested", "confirmed", "locked"]),
            ).order_by(orm.Event.created_at.desc())
        )
        return [EventMapper.to_domain(e) for e in result.scalars().all()]

    async def by_state(
        self,
        states: list[EventState],
        *,
        limit: int = 50,
    ) -> list[Event]:
        state_values = [s.value for s in states]
        result = await self._session.execute(
            select(orm.Event)
            .where(orm.Event.state.in_(state_values))
            .order_by(orm.Event.created_at.desc())
            .limit(limit)
        )
        return [EventMapper.to_domain(e) for e in result.scalars().all()]

    async def save(self, event: Event) -> Event:
        if event.event_id is not None:
            # Optimistic concurrency check
            result = await self._session.execute(
                select(orm.Event).where(orm.Event.event_id == event.event_id)
            )
            orm_event = result.scalar_one_or_none()
            if not orm_event:
                raise EntityNotFoundError(f"Event {event.event_id} not found.")
            if orm_event.version != event.version:
                raise ConcurrencyError(
                    f"Event {event.event_id} was modified by another process "
                    f"(expected version {event.version}, got {orm_event.version})"
                )
            EventMapper.to_orm(event, orm_event)
        else:
            orm_event = EventMapper.to_orm(event)
            self._session.add(orm_event)
            await self._session.flush()

        await self._session.refresh(orm_event)
        return EventMapper.to_domain(orm_event)

    async def delete(self, event_id: int) -> None:
        result = await self._session.execute(
            select(orm.Event).where(orm.Event.event_id == event_id)
        )
        orm_event = result.scalar_one_or_none()
        if orm_event:
            await self._session.delete(orm_event)


class SQLAlchemyParticipantRepository(IParticipantRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def by_event_and_user(
        self, event_id: int, telegram_user_id: int
    ) -> Optional[EventParticipant]:
        result = await self._session.execute(
            select(orm.EventParticipant).where(
                orm.EventParticipant.event_id == event_id,
                orm.EventParticipant.telegram_user_id == telegram_user_id,
            )
        )
        orm_p = result.scalar_one_or_none()
        return ParticipantMapper.to_domain(orm_p) if orm_p else None

    async def by_event(self, event_id: int) -> list[EventParticipant]:
        result = await self._session.execute(
            select(orm.EventParticipant)
            .where(orm.EventParticipant.event_id == event_id)
            .order_by(orm.EventParticipant.joined_at)
        )
        return [ParticipantMapper.to_domain(p) for p in result.scalars().all()]

    async def by_user(self, telegram_user_id: int) -> list[EventParticipant]:
        result = await self._session.execute(
            select(orm.EventParticipant)
            .where(orm.EventParticipant.telegram_user_id == telegram_user_id)
            .order_by(orm.EventParticipant.joined_at.desc())
        )
        return [ParticipantMapper.to_domain(p) for p in result.scalars().all()]

    async def by_status(
        self, event_id: int, status: ParticipantStatus
    ) -> list[EventParticipant]:
        result = await self._session.execute(
            select(orm.EventParticipant).where(
                orm.EventParticipant.event_id == event_id,
                orm.EventParticipant.status == orm.ParticipantStatus(status.value),
            )
        )
        return [ParticipantMapper.to_domain(p) for p in result.scalars().all()]

    async def save(self, participant: EventParticipant) -> EventParticipant:
        result = await self._session.execute(
            select(orm.EventParticipant).where(
                orm.EventParticipant.event_id == participant.event_id,
                orm.EventParticipant.telegram_user_id == participant.telegram_user_id,
            )
        )
        orm_p = result.scalar_one_or_none()

        orm_p = ParticipantMapper.to_orm(participant, orm_p)
        if not orm_p.event_id or not orm_p.telegram_user_id:
            self._session.add(orm_p)
        await self._session.flush()
        await self._session.refresh(orm_p)
        return ParticipantMapper.to_domain(orm_p)

    async def count_confirmed(self, event_id: int) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(orm.EventParticipant).where(
                orm.EventParticipant.event_id == event_id,
                orm.EventParticipant.status == orm.ParticipantStatus.confirmed,
            )
        )
        return int(result.scalar() or 0)


class SQLAlchemyConstraintRepository(IConstraintRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def by_event(self, event_id: int) -> list[Constraint]:
        result = await self._session.execute(
            select(orm.Constraint).where(orm.Constraint.event_id == event_id)
        )
        return [ConstraintMapper.to_domain(c) for c in result.scalars().all()]

    async def by_user(self, user_id: int) -> list[Constraint]:
        result = await self._session.execute(
            select(orm.Constraint).where(orm.Constraint.user_id == user_id)
        )
        return [ConstraintMapper.to_domain(c) for c in result.scalars().all()]

    async def save(self, constraint: Constraint) -> Constraint:
        if constraint.constraint_id:
            result = await self._session.execute(
                select(orm.Constraint).where(
                    orm.Constraint.constraint_id == constraint.constraint_id
                )
            )
            existing = result.scalar_one_or_none()
            orm_c = ConstraintMapper.to_orm(constraint, existing)
        else:
            orm_c = ConstraintMapper.to_orm(constraint)
            self._session.add(orm_c)

        await self._session.flush()
        await self._session.refresh(orm_c)
        return ConstraintMapper.to_domain(orm_c)


class SQLAlchemyStateTransitionRepository(IStateTransitionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, transition: StateTransition) -> StateTransition:
        orm_st = StateTransitionMapper.to_orm(transition)
        self._session.add(orm_st)
        await self._session.flush()
        await self._session.refresh(orm_st)
        return StateTransitionMapper.to_domain(orm_st)

    async def by_event(self, event_id: int) -> list[StateTransition]:
        result = await self._session.execute(
            select(orm.EventStateTransition)
            .where(orm.EventStateTransition.event_id == event_id)
            .order_by(orm.EventStateTransition.timestamp.desc())
        )
        return [StateTransitionMapper.to_domain(st) for st in result.scalars().all()]


# ---------------------------------------------------------------------------
# Unit of Work
# ---------------------------------------------------------------------------

class SQLAlchemyEventStore(IEventStore):
    """Unit of Work — wraps an async session, exposes repositories."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def begin(self) -> None:
        self._session = self._session_factory()

    async def commit(self) -> None:
        if self._session:
            try:
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                raise

    async def rollback(self) -> None:
        if self._session:
            await self._session.rollback()

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("EventStore not started. Call begin() first.")
        return self._session

    @property
    def users(self) -> IUserRepository:
        return SQLAlchemyUserRepository(self.session)

    @property
    def groups(self) -> IGroupRepository:
        return SQLAlchemyGroupRepository(self.session)

    @property
    def events(self) -> IEventRepository:
        return SQLAlchemyEventRepository(self.session)

    @property
    def participants(self) -> IParticipantRepository:
        return SQLAlchemyParticipantRepository(self.session)

    @property
    def constraints(self) -> IConstraintRepository:
        return SQLAlchemyConstraintRepository(self.session)

    @property
    def state_transitions(self) -> IStateTransitionRepository:
        return SQLAlchemyStateTransitionRepository(self.session)

    async def __aenter__(self) -> "SQLAlchemyEventStore":
        await self.begin()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.close()


def create_event_store(database_url: str) -> SQLAlchemyEventStore:
    """Factory for the event store."""
    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return SQLAlchemyEventStore(session_factory)
