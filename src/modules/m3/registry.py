"""
M3 IdentityOS — Event Registry registration.

Registers handlers for all M3 event types so that dispatch(event) routes m3.* to the M3 pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.modules.m3.events import M3_EVENT_TYPES
from src.modules.m3.handlers import handle_m3_event

if TYPE_CHECKING:
    from src.core.event_registry import EventRegistry


def register_m3_handlers(registry: "EventRegistry") -> None:
    """Register handle_m3_event for every M3 event type."""
    for event_type in M3_EVENT_TYPES:
        registry.register(event_type, handle_m3_event)
