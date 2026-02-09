"""
Event Registry — Maps event types to handlers.

Central dispatch: event_type → handler(event).
Used by Kafka processor and API to route ingest.v1, agent_run.v1, etc.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from src.models.event import CanonicalEvent, EVENT_TYPE_INGEST, EVENT_TYPE_AGENT_RUN

logger = logging.getLogger(__name__)

HandlerFn = Callable[[CanonicalEvent], Awaitable[Any]]


class EventRegistry:
    """
    Maps event types to async handlers.
    Handlers receive CanonicalEvent and perform type-specific logic.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, HandlerFn] = {}

    def register(self, event_type: str, handler: HandlerFn) -> None:
        """Register a handler for an event type. Overwrites existing."""
        self._handlers[event_type] = handler
        logger.info("EventRegistry: registered handler for %s", event_type)

    def get(self, event_type: str) -> HandlerFn | None:
        """Get handler for event type. Also checks .v1 suffix fallback (e.g. ingest -> ingest.v1)."""
        h = self._handlers.get(event_type)
        if h is not None:
            return h
        # Fallback: ingest -> ingest.v1, agent_run -> agent_run.v1
        if event_type == "ingest":
            return self._handlers.get(EVENT_TYPE_INGEST)
        if event_type == "agent_run":
            return self._handlers.get(EVENT_TYPE_AGENT_RUN)
        return None

    async def dispatch(self, event: CanonicalEvent) -> Any:
        """Dispatch event to registered handler. Raises KeyError if no handler."""
        handler = self.get(event.event_type)
        if handler is None:
            raise KeyError(f"No handler for event_type={event.event_type}")
        return await handler(event)

    def list_types(self) -> list[str]:
        """List registered event types."""
        return list(self._handlers.keys())


_registry: EventRegistry | None = None


def get_event_registry() -> EventRegistry:
    """Singleton EventRegistry with default handlers registered."""
    global _registry
    if _registry is None:
        _registry = EventRegistry()
        _register_default_handlers(_registry)
    return _registry


def _register_default_handlers(registry: EventRegistry) -> None:
    """Register built-in handlers for ingest.v1 and agent_run.v1."""
    from src.core.event_registry_handlers import handle_ingest_v1, handle_agent_run_v1

    registry.register(EVENT_TYPE_INGEST, handle_ingest_v1)
    registry.register(EVENT_TYPE_AGENT_RUN, handle_agent_run_v1)
    # Legacy type names
    registry.register("ingest", handle_ingest_v1)
    registry.register("agent_run", handle_agent_run_v1)
