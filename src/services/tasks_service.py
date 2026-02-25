"""
Read-only Tasks service.

Phase 4.2: exposes list/get functionality. For now it returns empty
collections; later phases will back it with Postgres/Redis/Kafka data.
"""

from __future__ import annotations

from typing import List, Optional

from src.schemas.api_models import Task


async def list_tasks(
    queue: Optional[str] = None,
    status: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
) -> List[Task]:
    """List tasks. Phase 4.2: returns an empty list."""
    return []


async def get_task(task_id: str) -> Optional[Task]:
    """Get a single task by ID. Phase 4.2: returns None."""
    return None


async def retry_task(task_id: str) -> bool:
    """Queue task for retry. Phase 4.2: no-op but returns True so API returns 200."""
    # When tasks are backed by store, re-queue or set status to pending here.
    return True

