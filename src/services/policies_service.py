"""
Read-only Policies service.

Phase 4.2: exposes list/get operations. For now it returns empty collections;
later phases will back it with Postgres models.
"""

from __future__ import annotations

from typing import List, Optional

from src.schemas.api_models import Policy


async def list_policies() -> List[Policy]:
    """List policies. Phase 4.2: returns an empty list."""
    return []


async def get_policy(policy_id: str) -> Optional[Policy]:
    """Get a single policy by ID. Phase 4.2: returns None."""
    return None

