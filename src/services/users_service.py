"""
Read-only Users & Roles service.

Phase 4.2: exposes list operations. For now it returns empty collections;
later phases will back it with Postgres models.
"""

from __future__ import annotations

from typing import List

from src.schemas.api_models import User, Role


async def list_users() -> List[User]:
    """List users. Phase 4.2: returns an empty list."""
    return []


async def list_roles() -> List[Role]:
    """List roles. Phase 4.2: returns an empty list."""
    return []

