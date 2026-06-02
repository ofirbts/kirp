"""
Single construction path for EventPipeline in workers and event-registry handlers.

API requests use ``main.get_pipeline()`` (cached singletons + shared RAG). Everything
that today built EventPipeline manually with fresh store/rag/schema should call
``create_connected_event_pipeline`` here so wiring stays consistent.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def create_connected_event_pipeline() -> Any:
    """
    Build EventPipeline using the unified ServiceRegistry.
    """
    from src.core.registry import get_registry
    return await get_registry().get_pipeline()
