"""
Audit service — Postgres-backed list.

Reads from audit_logs. Map to API AuditEntry (actorType, actorId, resourceType, action, result).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select

from src.core.schema_engine import get_schema_engine
from src.models.event import AuditLog
from src.schemas.api_models import AuditEntry


def _row_to_entry(row: AuditLog) -> AuditEntry:
    ts = row.timestamp.isoformat().replace("+00:00", "Z") if row.timestamp else ""
    return AuditEntry(
        id=str(row.id),
        timestamp=ts,
        actorType="user",
        actorId=row.user_id,
        tenantId=row.tenant_id,
        spaceId=None,
        action=row.action,
        resourceType=row.resource,
        resourceId=row.resource_id,
        metadata=row.details or {},
        result="success" if (row.result or "").lower() in ("allowed", "approved", "success") else "failure",
    )


async def list_audit_entries(
    actor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
) -> List[AuditEntry]:
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        q = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(500)
        result = await session.execute(q)
        rows = result.scalars().all()
        entries = [_row_to_entry(r) for r in rows]
        if tenant_id:
            entries = [e for e in entries if e.tenantId == tenant_id]
        if actor_id:
            entries = [e for e in entries if e.actorId == actor_id]
        if resource_type:
            entries = [e for e in entries if e.resourceType == resource_type]
        if action:
            entries = [e for e in entries if e.action == action]
        if from_ts:
            try:
                since = datetime.fromisoformat(from_ts.replace("Z", "+00:00"))
                entries = [e for e in entries if e.timestamp and e.timestamp >= since.isoformat()]
            except Exception:
                pass
        if to_ts:
            try:
                until = datetime.fromisoformat(to_ts.replace("Z", "+00:00"))
                entries = [e for e in entries if e.timestamp and e.timestamp <= until.isoformat()]
            except Exception:
                pass
        return entries
    finally:
        await session.close()
