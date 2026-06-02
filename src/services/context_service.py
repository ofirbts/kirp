"""
Context service — Accessible spaces, visibility, membership.

Respects SpaceMembership and visibility rules (private / shared / tenant / space).
Used by RAG, SchemaEngine, and API to scope queries to what the user can see.
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.schema_engine import get_schema_engine

logger = logging.getLogger(__name__)

# Visibility: convention for space_id
# "all" = tenant-wide (everyone in tenant can request it)
# specific space_id = only members of that space (from SpaceMembership) can see it


async def get_accessible_space_ids(tenant_id: str, user_id: str) -> list[str]:
    """
    Return list of space_ids the user is allowed to access in this tenant.
    Always includes "all" for backward compatibility. Adds any space_id from SpaceMembership.
    """
    try:
        engine = await get_schema_engine()
        session = await engine.get_session()
        from sqlalchemy import select
        from src.models.space_membership import SpaceMembership
        async with session:
            stmt = select(SpaceMembership.space_id).where(
                SpaceMembership.tenant_id == tenant_id,
                SpaceMembership.user_id == user_id,
            ).distinct()
            result = await session.execute(stmt)
            space_ids = [row[0] for row in result.fetchall()]
        if "all" not in space_ids:
            space_ids.append("all")
        return space_ids
    except Exception as e:
        logger.warning("get_accessible_space_ids failed: %s", e)
        return ["all"]


async def can_access_space(tenant_id: str, user_id: str, space_id: str) -> bool:
    """True if user can access the given (tenant_id, space_id)."""
    if not space_id or space_id == "all":
        return True
    allowed = await get_accessible_space_ids(tenant_id, user_id)
    return space_id in allowed


async def list_spaces_for_context(tenant_id: str, user_id: str) -> list[dict[str, Any]]:
    """
    Return list of { space_id, role? } for context switching (UI dropdown).
    """
    try:
        engine = await get_schema_engine()
        session = await engine.get_session()
        from sqlalchemy import select
        from src.models.space_membership import SpaceMembership
        async with session:
            stmt = select(SpaceMembership.space_id, SpaceMembership.role).where(
                SpaceMembership.tenant_id == tenant_id,
                SpaceMembership.user_id == user_id,
            )
            result = await session.execute(stmt)
            rows = list(result.fetchall())
            spaces = [{"space_id": r[0], "role": r[1]} for r in rows]
        if not any(s["space_id"] == "all" for s in spaces):
            spaces.insert(0, {"space_id": "all", "role": None})
        return spaces
    except Exception as e:
        logger.warning("list_spaces_for_context failed: %s", e)
        return [{"space_id": "all", "role": None}]
