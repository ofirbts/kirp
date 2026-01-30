"""
Read-only Audit service.

Phase 4.2: exposes list operation for audit entries. For now it returns an
empty collection; later phases will back it with Postgres projections.
"""

from __future__ import annotations

from typing import List, Optional

from src.schemas.api_models import AuditEntry


async def list_audit_entries(
    actor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
) -> List[AuditEntry]:
    """List audit entries. Phase 4.2: returns an empty list."""
    return []

