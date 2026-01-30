"""
Read-only Tenants service.

Phase 4.2: exposes list operations for tenants and spaces. For now it returns
empty collections; later phases will back it with Postgres models.
"""

from __future__ import annotations

from typing import List

from src.schemas.api_models import Tenant, Space


async def list_tenants() -> List[Tenant]:
    """List tenants. Phase 4.2: returns an empty list."""
    return []


async def list_spaces_for_tenant(tenant_id: str) -> List[Space]:
    """List spaces for a tenant. Phase 4.2: returns an empty list."""
    return []

