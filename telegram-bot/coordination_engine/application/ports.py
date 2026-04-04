"""Application service ports — interfaces for infrastructure services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IMessageService(ABC):
    """Port for sending messages to Telegram users/groups."""

    @abstractmethod
    async def send_to_user(
        self,
        telegram_user_id: int,
        text: str,
        *,
        parse_mode: str = "Markdown",
        reply_markup: Any = None,
    ) -> bool: ...

    @abstractmethod
    async def send_to_chat(
        self,
        chat_id: int,
        text: str,
        *,
        parse_mode: str = "Markdown",
        reply_markup: Any = None,
        reply_to_message_id: int | None = None,
    ) -> bool: ...


class ILLMService(ABC):
    """Port for AI/LLM operations."""

    @abstractmethod
    async def infer_event_draft(
        self,
        message_text: str,
        history: list[dict[str, Any]] | None = None,
        scheduling_mode: str = "fixed",
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def infer_modification_patch(
        self,
        current_draft: dict[str, Any],
        change_text: str,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def infer_mention_action(
        self,
        text: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def infer_constraint(
        self, text: str
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def generate_memory_weave(
        self, fragments: list[str], event_type: str
    ) -> dict[str, Any]: ...


class ISchedulerService(ABC):
    """Port for background job scheduling."""

    @abstractmethod
    async def schedule_once(
        self,
        job_name: str,
        callback: Any,
        run_time: Any,
        context: dict[str, Any] | None = None,
    ) -> None: ...

    @abstractmethod
    async def schedule_recurring(
        self,
        job_name: str,
        callback: Any,
        interval_seconds: int,
        context: dict[str, Any] | None = None,
    ) -> None: ...

    @abstractmethod
    async def cancel_job(self, job_name: str) -> None: ...


class INotificationService(ABC):
    """Port for domain-specific notifications."""

    @abstractmethod
    async def notify_event_created(self, event_id: int, organizer_id: int) -> None: ...

    @abstractmethod
    async def notify_event_modified(
        self, event_id: int, changed_fields: list[str]
    ) -> None: ...

    @abstractmethod
    async def notify_participant_joined(
        self, event_id: int, telegram_user_id: int
    ) -> None: ...

    @abstractmethod
    async def notify_threshold_reached(
        self, event_id: int, count: int, threshold: int
    ) -> None: ...

    @abstractmethod
    async def notify_event_locked(self, event_id: int) -> None: ...

    @abstractmethod
    async def notify_event_completed(self, event_id: int) -> None: ...

    @abstractmethod
    async def notify_event_cancelled(self, event_id: int, reason: str) -> None: ...

    @abstractmethod
    async def request_memory_collection(self, event_id: int) -> None: ...
