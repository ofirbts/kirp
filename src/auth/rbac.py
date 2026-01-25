"""
RBAC Engine — Roles, permissions, access control.

Access Control Matrix:
- Private → Owner only
- Shared → Explicit permissions
- Org → RBAC + ABAC + Policies
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    APPROVE = "approve"


@dataclass
class AccessCheck:
    allowed: bool
    reason: str


class RBACEngine:
    """
    Role-based access control. Integrates with OPA for policy overlay.
    """

    def __init__(self, postgres_uri: str, opa_url: str | None = None) -> None:
        self._postgres_uri = postgres_uri
        self._opa_url = opa_url
        self._session_factory: Any = None

    async def connect(self) -> None:
        """Initialize DB connection."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
            engine = create_async_engine(self._postgres_uri, echo=False)
            self._session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            logger.info("RBACEngine connected")
        except Exception as e:
            logger.error("RBACEngine connection failed: %s", e)
            raise

    async def get_role(self, tenant_id: str, space_id: str, user_id: str) -> Role | None:
        """Get user role in space."""
        if self._session_factory is None:
            await self.connect()
        # TODO: Query role from DB
        return Role.MEMBER

    async def check(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        permission: Permission,
        resource: str,
    ) -> AccessCheck:
        """Check if user has permission on resource in space."""
        role = await self.get_role(tenant_id, space_id, user_id)
        if role is None:
            return AccessCheck(allowed=False, reason="no_role")
        # Simple matrix: owner/admin have all; member read+write; viewer read
        if role in (Role.OWNER, Role.ADMIN):
            return AccessCheck(allowed=True, reason="role")
        if permission == Permission.READ and role in (Role.MEMBER, Role.VIEWER, Role.GUEST):
            return AccessCheck(allowed=True, reason="role")
        if permission == Permission.WRITE and role == Role.MEMBER:
            return AccessCheck(allowed=True, reason="role")
        return AccessCheck(allowed=False, reason=f"insufficient_role:{role.value}")
