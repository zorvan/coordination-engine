"""Repository interfaces (ports) — defined in domain, implemented in infrastructure."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from coordination_engine.domain.entities import (
    Constraint,
    Event,
    EventParticipant,
    Group,
    StateTransition,
    User,
)
from coordination_engine.domain.value_objects import (
    EventState,
    ParticipantStatus,
)


class IUserRepository(ABC):
    @abstractmethod
    async def by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    async def by_telegram_id(self, telegram_user_id: int) -> Optional[User]: ...

    @abstractmethod
    async def by_username(self, username: str) -> Optional[User]: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...

    @abstractmethod
    async def get_or_create_by_telegram(
        self,
        telegram_user_id: int,
        *,
        username: str | None = None,
        display_name: str | None = None,
    ) -> User: ...


class IGroupRepository(ABC):
    @abstractmethod
    async def by_id(self, group_id: int) -> Optional[Group]: ...

    @abstractmethod
    async def by_telegram_id(self, telegram_group_id: int) -> Optional[Group]: ...

    @abstractmethod
    async def save(self, group: Group) -> Group: ...

    @abstractmethod
    async def ensure_exists(
        self,
        telegram_group_id: int,
        *,
        group_name: str | None = None,
    ) -> Group: ...


class IEventRepository(ABC):
    @abstractmethod
    async def by_id(self, event_id: int) -> Optional[Event]: ...

    @abstractmethod
    async def active_for_group(self, group_id: int) -> list[Event]: ...

    @abstractmethod
    async def active_for_user(self, telegram_user_id: int) -> list[Event]: ...

    @abstractmethod
    async def by_state(
        self,
        states: list[EventState],
        *,
        limit: int = 50,
    ) -> list[Event]: ...

    @abstractmethod
    async def save(self, event: Event) -> Event: ...

    @abstractmethod
    async def delete(self, event_id: int) -> None: ...


class IParticipantRepository(ABC):
    @abstractmethod
    async def by_event_and_user(
        self, event_id: int, telegram_user_id: int
    ) -> Optional[EventParticipant]: ...

    @abstractmethod
    async def by_event(self, event_id: int) -> list[EventParticipant]: ...

    @abstractmethod
    async def by_user(self, telegram_user_id: int) -> list[EventParticipant]: ...

    @abstractmethod
    async def by_status(
        self, event_id: int, status: ParticipantStatus
    ) -> list[EventParticipant]: ...

    @abstractmethod
    async def save(self, participant: EventParticipant) -> EventParticipant: ...

    @abstractmethod
    async def count_confirmed(self, event_id: int) -> int: ...


class IConstraintRepository(ABC):
    @abstractmethod
    async def by_event(self, event_id: int) -> list[Constraint]: ...

    @abstractmethod
    async def by_user(self, user_id: int) -> list[Constraint]: ...

    @abstractmethod
    async def save(self, constraint: Constraint) -> Constraint: ...


class IStateTransitionRepository(ABC):
    @abstractmethod
    async def record(self, transition: StateTransition) -> StateTransition: ...

    @abstractmethod
    async def by_event(self, event_id: int) -> list[StateTransition]: ...


class IEventStore(ABC):
    """Unit-of-Work interface for transactional operations."""

    @abstractmethod
    async def begin(self) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    # Repositories exposed through the UoW
    @property
    @abstractmethod
    def users(self) -> IUserRepository: ...

    @property
    @abstractmethod
    def groups(self) -> IGroupRepository: ...

    @property
    @abstractmethod
    def events(self) -> IEventRepository: ...

    @property
    @abstractmethod
    def participants(self) -> IParticipantRepository: ...

    @property
    @abstractmethod
    def constraints(self) -> IConstraintRepository: ...

    @property
    @abstractmethod
    def state_transitions(self) -> IStateTransitionRepository: ...
