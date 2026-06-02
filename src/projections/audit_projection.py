"""
Audit projections.

Translate governance / audit events into `AuditLog` rows in Postgres.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AuditLog


async def record_audit_entry(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    result: str,
    policy_id: Optional[str] = None,
    risk_score: Optional[float] = None,
    details: Optional[Mapping[str, Any]] = None,
    timestamp: Optional[datetime] = None,
) -> AuditLog:
    """
    Insert an audit log row.

    This function does not commit; callers are responsible for committing.
    """
    ts = timestamp or datetime.utcnow()
    entry = AuditLog(
        id=uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        result=result,
        policy_id=policy_id,
        risk_score=risk_score,
        details=dict(details or {}),
        timestamp=ts,
    )
    session.add(entry)
    await session.flush()
    return entry

