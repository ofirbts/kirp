"""
Users & Roles service — Postgres-backed list.

Uses SchemaEngine (Postgres) for User and Role. Idempotent initialization:
create_role_if_not_exists, ensure_default_user (no duplicate roles).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.core.schema_engine import get_schema_engine
from src.models.user import User, Role, user_roles
from src.schemas.api_models import User as UserSchema, Role as RoleSchema, Permission


async def get_or_create_role_in_session(
    session: Any,
    name: str,
    tenant_id: str | None = None,
    permissions: List[str] | None = None,
    now: datetime | None = None,
) -> Role:
    """Within an existing async session: get role by name or create. No commit. Idempotent."""
    result = await session.execute(select(Role).where(Role.name == name).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    role = Role(
        id=uuid.uuid4(),
        name=name,
        tenant_id=tenant_id,
        permissions=permissions or [],
        created_at=now or datetime.now(timezone.utc),
    )
    session.add(role)
    await session.flush()
    return role


async def create_role_if_not_exists(
    name: str,
    tenant_id: str | None = None,
    permissions: List[str] | None = None,
) -> str:
    """Create a role by name if it does not exist. Returns role id (str). Idempotent."""
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(select(Role).where(Role.name == name).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            return str(existing.id)
        role = Role(
            id=uuid.uuid4(),
            name=name,
            tenant_id=tenant_id,
            permissions=permissions or [],
            created_at=datetime.now(timezone.utc),
        )
        session.add(role)
        await session.commit()
        return str(role.id)
    except IntegrityError:
        await session.rollback()
        result = await session.execute(select(Role).where(Role.name == name).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            return str(existing.id)
        raise
    finally:
        await session.close()


def _user_to_schema(u: User, role_ids: List[str]) -> UserSchema:
    created = u.created_at.isoformat().replace("+00:00", "Z") if u.created_at else ""
    name = (u.extra or {}).get("name") if isinstance(u.extra, dict) else u.username
    return UserSchema(
        id=str(u.id),
        email=u.email or f"{u.username}@local",
        name=name or u.username,
        status=(u.extra or {}).get("status", "active") if isinstance(u.extra, dict) else "active",
        roles=role_ids,
        tenants=[u.tenant_id],
        spaces=[],
        createdAt=created,
        lastLoginAt=None,
    )


def _role_to_schema(r: Role) -> RoleSchema:
    created = r.created_at.isoformat().replace("+00:00", "Z") if r.created_at else ""
    perms = r.permissions or []
    return RoleSchema(
        id=str(r.id),
        name=r.name,
        description=None,
        inheritedRoleIds=None,
        permissions=[Permission(resource="*", action=p, scope="tenant") for p in (perms if perms else [])] if perms and isinstance(perms[0], str) else [Permission(resource="*", action="read", scope="tenant")],
    )


async def list_users() -> List[UserSchema]:
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(select(User).options(selectinload(User.roles)).order_by(User.username))
        users = result.scalars().unique().all()
        out = []
        for u in users:
            role_ids = [str(r.id) for r in (u.roles or [])]
            out.append(_user_to_schema(u, role_ids))
        if not out:
            await session.close()
            await ensure_default_user()
            session2 = await engine.get_session()
            try:
                result2 = await session2.execute(select(User).options(selectinload(User.roles)).order_by(User.username))
                users = result2.scalars().unique().all()
                return [_user_to_schema(u, [str(r.id) for r in (u.roles or [])]) for u in users]
            finally:
                await session2.close()
        return out
    finally:
        await session.close()


async def list_roles() -> List[RoleSchema]:
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(select(Role).order_by(Role.name))
        roles = result.scalars().all()
        out = [_role_to_schema(r) for r in roles]
        if not out:
            await session.close()
            await ensure_default_user()
            session2 = await engine.get_session()
            try:
                result2 = await session2.execute(select(Role).order_by(Role.name))
                roles = result2.scalars().all()
                return [_role_to_schema(r) for r in roles]
            finally:
                await session2.close()
        return out
    finally:
        await session.close()


async def ensure_default_user() -> None:
    """Create default user 'ofir' with role 'owner' if no user exists. Idempotent."""
    from src.services import tenants_service
    await tenants_service.ensure_default_tenant()
    engine = await get_schema_engine()
    session = await engine.get_session()
    try:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        from src.models.tenant import Tenant
        tenant_result = await session.execute(select(Tenant).order_by(Tenant.name).limit(1))
        tenant = tenant_result.scalar_one_or_none()
        tenant_id_str = str(tenant.id) if tenant else "default"
        owner_role_id = await create_role_if_not_exists(
            "owner",
            tenant_id=tenant_id_str,
            permissions=["read", "write", "execute", "admin"],
        )
        user = User(
            id=uuid.uuid4(),
            username="ofir",
            email="ofir@local",
            tenant_id=tenant_id_str,
            extra={"name": "Ofir", "status": "active"},
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.flush()
        await session.execute(user_roles.insert().values(user_id=user.id, role_id=uuid.UUID(owner_role_id)))
        await session.commit()
    except IntegrityError:
        await session.rollback()
    finally:
        await session.close()
