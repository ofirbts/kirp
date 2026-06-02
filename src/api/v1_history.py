"""
V1 History API — Human-readable timeline (History 2.0).

GET /api/v1/history?tenant_id&user_id&limit&type&from&to
Returns array of HistoryEntry, sorted by created_at desc.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.core.history import get_history_store
from src.auth.tenant_context import get_tenant_context, is_local_or_skip_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["V1 History"])


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.get("/history")
async def list_history_v1(
    request: Request,
    tenant_id: str | None = Query(None, description="Tenant ID (must match authenticated context)"),
    limit: int = Query(100, ge=1, le=500),
    type: str | None = Query(None, description="Filter by entry type"),
    from_: str | None = Query(None, alias="from", description="ISO datetime inclusive"),
    to: str | None = Query(None, description="ISO datetime inclusive"),
) -> list[dict[str, Any]]:
    """List history entries (human-readable timeline) for the authenticated tenant/user."""
    ctx = get_tenant_context(request)
    if not is_local_or_skip_auth() and tenant_id is not None and tenant_id.strip() != "" and tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    try:
        store = get_history_store()
        await store.connect()
        from_ts = _parse_iso(from_)
        to_ts = _parse_iso(to)
        entries = await store.list_(
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            limit=limit,
            type_filter=type,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        return [e.to_json() for e in entries]
    except Exception as e:
        logger.warning("History store unavailable: %s", e)
        return []
