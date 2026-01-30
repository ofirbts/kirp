"""
Admin bootstrap service.

This is the ONLY supported way to create the initial tenant, spaces, users
and roles in a clean production system. It uses the same PostgreSQL
infrastructure as the SchemaEngine (async SQLAlchemy).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tenant import Tenant, Space
from src.models.user import User, Role


class BootstrapError(Exception):
    """Bootstrap failed (validation or persistence error)."""


async def _tenant_exists(session: AsyncSession) -> bool:
    stmt = select(Tenant).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def bootstrap_system(
    session: AsyncSession,
    *,
    tenant_payload: Mapping[str, Any],
    spaces_payload: List[Mapping[str, Any]],
    users_payload: List[Mapping[str, Any]],
    roles_payload: List[Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Create initial tenant, spaces, users, and roles.

    Constraints:
    - Idempotent guard: if any tenant already exists, abort.
    - Caller is responsible for passing an open AsyncSession and committing
      or rolling back around this function.
    """
    if await _tenant_exists(session):
        raise BootstrapError("Bootstrap already performed (tenant exists)")

    now = datetime.now(timezone.utc)

    # --- Tenant ---
    tenant = Tenant(
        id=uuid4(),
        name=str(tenant_payload.get("name") or "").strip() or "Tenant",
        extra=tenant_payload.get("extra") or {},
        created_at=now,
        updated_at=now,
    )
    session.add(tenant)

    # --- Roles ---
    roles_by_name: dict[str, Role] = {}
    for role_spec in roles_payload:
        name = str(role_spec.get("name") or "").strip()
        if not name:
            raise BootstrapError("Role name is required")
        role = Role(
            id=uuid4(),
            name=name,
            tenant_id=str(tenant.id),
            permissions=role_spec.get("permissions") or [],
            created_at=now,
        )
        session.add(role)
        roles_by_name[name] = role

    # --- Spaces ---
    spaces_by_slug: dict[str, Space] = {}
    for space_spec in spaces_payload:
        name = str(space_spec.get("name") or "").strip()
        if not name:
            raise BootstrapError("Space name is required")
        kind = str(space_spec.get("kind") or "private")
        owner_id = space_spec.get("ownerId")
        space = Space(
            id=uuid4(),
            tenant_id=tenant.id,
            kind=kind,
            name=name,
            owner_id=owner_id,
            extra=space_spec.get("extra") or {},
            created_at=now,
            updated_at=now,
        )
        session.add(space)
        slug = str(space_spec.get("slug") or name.lower().replace(" ", "-"))
        spaces_by_slug[slug] = space

    # --- Users ---
    users: list[User] = []
    for user_spec in users_payload:
        email = str(user_spec.get("email") or "").strip()
        username = str(user_spec.get("username") or email or "").strip()
        if not email and not username:
            raise BootstrapError("User email or username is required")
        user = User(
            id=uuid4(),
            username=username or email,
            email=email or None,
            tenant_id=str(tenant.id),
            extra=user_spec.get("extra") or {},
            created_at=now,
        )
        session.add(user)
        users.append(user)

        # Attach roles by name or role_ids (seed uses role_ids)
        for role_key in user_spec.get("roles", []) or user_spec.get("role_ids", []):
            role_obj = roles_by_name.get(role_key)
            if role_obj:
                user.roles.append(role_obj)

    await session.flush()

    return {
        "tenantId": str(tenant.id),
        "spaceIds": [str(s.id) for s in spaces_by_slug.values()],
        "userIds": [str(u.id) for u in users],
        "roleIds": [str(r.id) for r in roles_by_name.values()],
    }

