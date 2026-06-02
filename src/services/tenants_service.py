"""
Tenants service — Postgres-backed list and create.

Uses SchemaEngine (Postgres) for Tenant and Space. Idempotent initialization:
create_tenant_if_not_exists, create_space_if_not_exists, ensure_default_tenant.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.core.schema_engine import get_schema_engine
from src.models.tenant import Tenant, Space
from src.schemas.api_models import Tenant as TenantSchema, Space as SpaceSchema

# SaaS tenant lifecycle (path C — Stripe/onboarding). Persisted in Tenant.extra["lifecycle"]; no migration.
_LIFECYCLE_EXTRA_KEY = "lifecycle"
_VALID_LIFECYCLES = frozenset(
    {
        "pending_onboarding",
        "trial",
        "active",
        "limited",
        "past_due",
        "suspended",
    }
)

# Dashboard email/password signup: align with API-key onboarding trial length (onboarding_service.TRIAL_DAYS).
_SAAS_SIGNUP_TRIAL_DAYS = 30


class TenantLifecycleError(ValueError):
    """Invalid tenant id, unknown tenant, or invalid lifecycle value."""


def _lifecycle_from_extra(extra: dict | None) -> str:
    raw = (extra or {}).get(_LIFECYCLE_EXTRA_KEY)
    if isinstance(raw, str) and raw in _VALID_LIFECYCLES:
        return raw
    return "active"


async def create_tenant_if_not_exists(
    name: str = "Default",
    slug: str | None = "default",
) -> str:
    """Create a tenant if none with this slug/name exists. Returns tenant id (str). Idempotent."""
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(
            select(Tenant).where(Tenant.name == name).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return str(existing.id)
        tenant = Tenant(
            id=uuid.uuid4(),
            name=name,
            extra={
                "slug": slug or _slug(name),
                _LIFECYCLE_EXTRA_KEY: "active",
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(tenant)
        await session.commit()
        return str(tenant.id)
    except IntegrityError:
        await session.rollback()
        result = await session.execute(select(Tenant).where(Tenant.name == name).limit(1))
        existing = result.scalar_one_or_none()
        return str(existing.id) if existing else ""
    finally:
        await session.close()


async def create_space_if_not_exists(
    tenant_id: str,
    name: str = "all",
    kind: str = "shared",
) -> str:
    """Create a space for the tenant if one with this name does not exist. Returns space id (str). Idempotent."""
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        tenant_uuid = uuid.UUID(tenant_id)
        result = await session.execute(
            select(Space).where(
                Space.tenant_id == tenant_uuid,
                Space.name == name,
            ).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return str(existing.id)
        space = Space(
            id=uuid.uuid4(),
            tenant_id=tenant_uuid,
            kind=kind,
            name=name,
            extra={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(space)
        await session.commit()
        return str(space.id)
    except IntegrityError:
        await session.rollback()
        result = await session.execute(
            select(Space).where(
                Space.tenant_id == uuid.UUID(tenant_id),
                Space.name == name,
            ).limit(1)
        )
        existing = result.scalar_one_or_none()
        return str(existing.id) if existing else ""
    finally:
        await session.close()


def _slug(s: str) -> str:
    return (s or "").lower().replace(" ", "-").replace("_", "-")[:64]


def _tenant_to_schema(t: Tenant) -> TenantSchema:
    created = t.created_at.isoformat().replace("+00:00", "Z") if t.created_at else ""
    updated = t.updated_at.isoformat().replace("+00:00", "Z") if t.updated_at else ""
    return TenantSchema(
        id=str(t.id),
        name=t.name,
        slug=(t.extra or {}).get("slug") or _slug(t.name),
        lifecycle=_lifecycle_from_extra(t.extra),
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
    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except (ValueError, TypeError):
        return []
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(
            select(Space).where(Space.tenant_id == tenant_uuid).order_by(Space.name)
        )
        spaces = result.scalars().all()
        return [_space_to_schema(s) for s in spaces]
    finally:
        await session.close()


async def seed_saas_trial_for_signup(tenant_id: str, email: str, trial_days: int | None = None) -> None:
    """
    After ``/api/v1/auth/signup``: move tenant from ``pending_onboarding`` to ``trial``
    with ``trial_ends_at`` and ``onboarding_email`` so billing / usage match Stripe flows.
    """
    days = trial_days if trial_days is not None else _SAAS_SIGNUP_TRIAL_DAYS
    try:
        tid = uuid.UUID(tenant_id)
    except (ValueError, TypeError) as e:
        raise TenantLifecycleError("invalid tenant id") from e

    now = datetime.now(timezone.utc)
    trial_end = now + timedelta(days=days)
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(select(Tenant).where(Tenant.id == tid).limit(1))
        row = result.scalar_one_or_none()
        if row is None:
            raise TenantLifecycleError("tenant not found")
        ex = dict(row.extra or {})
        ex[_LIFECYCLE_EXTRA_KEY] = "trial"
        ex["trial_ends_at"] = trial_end.isoformat().replace("+00:00", "Z")
        em = (email or "").strip().lower()
        if em:
            ex["onboarding_email"] = em
        row.extra = ex
        row.updated_at = now
        await session.commit()
    finally:
        await session.close()


async def update_tenant_lifecycle(tenant_id: str, lifecycle: str) -> TenantSchema:
    """
    Persist SaaS lifecycle on Tenant.extra (Stripe/onboarding callbacks and admin UI).

    ``tenant_id`` must be the Postgres tenant UUID string.
    """
    life = lifecycle.strip()
    if life not in _VALID_LIFECYCLES:
        raise TenantLifecycleError(f"invalid lifecycle: {life!r}")
    try:
        tid = uuid.UUID(tenant_id)
    except (ValueError, TypeError) as e:
        raise TenantLifecycleError("invalid tenant id") from e

    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(select(Tenant).where(Tenant.id == tid).limit(1))
        row = result.scalar_one_or_none()
        if row is None:
            raise TenantLifecycleError("tenant not found")
        ex = dict(row.extra or {})
        ex[_LIFECYCLE_EXTRA_KEY] = life
        row.extra = ex
        row.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(row)
        return _tenant_to_schema(row)
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
            extra={**({"slug": s}), _LIFECYCLE_EXTRA_KEY: "pending_onboarding"},
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
    """Ensure default tenant and default space exist. Idempotent."""
    tenant_id = await create_tenant_if_not_exists(name="Default", slug="default")
    if tenant_id:
        await create_space_if_not_exists(tenant_id, name="all", kind="shared")
