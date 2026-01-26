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
        """Get user role in space from database."""
        if self._session_factory is None:
            await self.connect()
        
        try:
            from sqlalchemy import select
            from src.models.user import User, Role as RoleModel
            from sqlalchemy.orm import selectinload
            
            async with self._session_factory() as session:
                # Query user with roles
                stmt = select(User).where(
                    User.tenant_id == tenant_id,
                    User.id == user_id if isinstance(user_id, str) else user_id,
                ).options(selectinload(User.roles))
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    return None
                
                # Get highest privilege role
                role_names = [r.name for r in user.roles] if user.roles else []
                
                # Map to enum (priority order)
                if "owner" in role_names or Role.OWNER.value in role_names:
                    return Role.OWNER
                if "admin" in role_names or Role.ADMIN.value in role_names:
                    return Role.ADMIN
                if "member" in role_names or Role.MEMBER.value in role_names:
                    return Role.MEMBER
                if "viewer" in role_names or Role.VIEWER.value in role_names:
                    return Role.VIEWER
                if "guest" in role_names or Role.GUEST.value in role_names:
                    return Role.GUEST
                
                # Default to member if user exists but no roles
                return Role.MEMBER
        except Exception as e:
            logger.warning("Failed to query role from DB: %s, using default", e)
            return Role.MEMBER  # Default fallback

    async def check(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        permission: Permission,
        resource: str,
        resource_attributes: dict[str, Any] | None = None,
    ) -> AccessCheck:
        """
        Check if user has permission on resource (RBAC + ABAC).
        Enforces multi-tenant isolation.
        """
        # Enforce multi-tenant isolation
        if not tenant_id or tenant_id == "*":
            return AccessCheck(allowed=False, reason="invalid_tenant_id")
        
        # RBAC check
        role = await self.get_role(tenant_id, space_id, user_id)
        if role is None:
            return AccessCheck(allowed=False, reason="no_role")
        
        # Role-based permissions
        role_allowed = False
        if role in (Role.OWNER, Role.ADMIN):
            role_allowed = True
        elif permission == Permission.READ and role in (Role.MEMBER, Role.VIEWER, Role.GUEST):
            role_allowed = True
        elif permission == Permission.WRITE and role == Role.MEMBER:
            role_allowed = True
        elif permission == Permission.APPROVE and role in (Role.OWNER, Role.ADMIN):
            role_allowed = True
        
        # ABAC check (if OPA available)
        abac_allowed = True
        if self._opa_url and resource_attributes:
            try:
                import httpx
                payload = {
                    "input": {
                        "tenant_id": tenant_id,
                        "space_id": space_id,
                        "user_id": user_id,
                        "user_role": role.value,
                        "permission": permission.value,
                        "resource": resource,
                        "resource_attributes": resource_attributes or {},
                    }
                }
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"{self._opa_url}/v1/data/kirp/abac/allow",
                        json=payload,
                        timeout=2.0,
                    )
                if r.status_code == 200:
                    data = r.json()
                    abac_allowed = data.get("result", {}).get("allow", True)
                else:
                    logger.warning("ABAC check failed: %s", r.status_code)
            except Exception as e:
                logger.warning("ABAC check error: %s", e)
                # Fail open if ABAC unavailable
        
        # Both RBAC and ABAC must allow
        allowed = role_allowed and abac_allowed
        reason = "rbac+abac" if allowed else f"rbac={role_allowed},abac={abac_allowed}"
        
        return AccessCheck(allowed=allowed, reason=reason)
