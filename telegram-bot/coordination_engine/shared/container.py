"""Dependency injection container."""

from __future__ import annotations

from typing import Any, Callable


class Container:
    """Simple DI container with singleton and factory support."""

    def __init__(self) -> None:
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}
        self._instances: dict[str, Any] = {}

    def register_singleton(self, key: str, factory: Callable[[], Any]) -> None:
        self._factories[key] = factory

    def register_instance(self, key: str, instance: Any) -> None:
        self._singletons[key] = instance

    def resolve(self, key: str) -> Any:
        if key in self._singletons:
            return self._singletons[key]

        if key not in self._factories:
            raise KeyError(f"No registration for '{key}'")

        if key not in self._instances:
            self._instances[key] = self._factories[key]()

        return self._instances[key]

    async def resolve_async(self, key: str) -> Any:
        if key in self._singletons:
            return self._singletons[key]

        if key not in self._factories:
            raise KeyError(f"No registration for '{key}'")

        if key not in self._instances:
            self._instances[key] = await self._factories[key]()

        return self._instances[key]

    def reset(self) -> None:
        """Clear cached instances (useful for testing)."""
        self._instances.clear()
