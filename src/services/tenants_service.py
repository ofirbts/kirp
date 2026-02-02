"""
Tenants service — Postgres-backed list and create.

Uses SchemaEngine (Postgres) for Tenant and Space. Ensures default tenant/space exist.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select

from src.core.schema_engine import get_schema_engine
from src.models.tenant import Tenant, Space
from src.schemas.api_models import Tenant as TenantSchema, Space as SpaceSchema


def _slug(s: str) -> str:
    return (s or "").lower().replace(" ", "-").replace("_", "-")[:64]


def _tenant_to_schema(t: Tenant) -> TenantSchema:
    created = t.created_at.isoformat().replace("+00:00", "Z") if t.created_at else ""
    updated = t.updated_at.isoformat().replace("+00:00", "Z") if t.updated_at else ""
    return TenantSchema(
        id=str(t.id),
        name=t.name,
        slug=(t.extra or {}).get("slug") or _slug(t.name),
        createdAt=created,
        updatedAt=updated,
    )


def _space_to_schema(s: Space) -> SpaceSchema:
    created = s.created_at.isoformat().replace("+00:00", "Z") if s.created_at else ""
    updated = s.updated_at.isoformat().replace("+00:00", "Z") if s.updated_at else ""
    return SpaceSchema(
        id=str(s.id),
        tenantId=str(s.tenant_id),
        name=s.name,
        slug=(s.extra or {}).get("slug") or _slug(s.name),
        createdAt=created,
        updatedAt=updated,
    )


async def list_tenants() -> List[TenantSchema]:
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(select(Tenant).order_by(Tenant.name))
        tenants = result.scalars().all()
        out = [_tenant_to_schema(t) for t in tenants]
        if not out:
            await session.close()
            await ensure_default_tenant()
            session2 = await engine.get_session()
            try:
                result2 = await session2.execute(select(Tenant).order_by(Tenant.name))
                tenants = result2.scalars().all()
                return [_tenant_to_schema(t) for t in tenants]
            finally:
                await session2.close()
        return out
    finally:
        await session.close()


async def list_spaces_for_tenant(tenant_id: str) -> List[SpaceSchema]:
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(
            select(Space).where(Space.tenant_id == uuid.UUID(tenant_id)).order_by(Space.name)
        )
        spaces = result.scalars().all()
        return [_space_to_schema(s) for s in spaces]
    finally:
        await session.close()


async def create_tenant(name: str, slug: str | None = None) -> TenantSchema:
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        s = slug or _slug(name)
        tenant = Tenant(
            id=uuid.uuid4(),
            name=name,
            extra={"slug": s},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(tenant)
        await session.flush()
        space = Space(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            kind="shared",
            name="all",
            extra={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(space)
        await session.commit()
        await session.refresh(tenant)
        return _tenant_to_schema(tenant)
    finally:
        await session.close()


async def ensure_default_tenant() -> None:
    """Create default tenant and space if none exist."""
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(select(Tenant).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Default",
            extra={"slug": "default"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(tenant)
        await session.flush()
        space = Space(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            kind="shared",
            name="all",
            extra={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(space)
        await session.commit()
    finally:
        await session.close()
