"""
Tenant Engine — Multi-tenant hierarchy.

Root Tenant (Organization)
├── User Private Space
├── Shared Spaces (Family / Partners / Teams)
└── Org Space (Company-wide)

Zero leakage: no cross-tenant access unless explicitly granted.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SpaceKind(str, Enum):
    PRIVATE = "private"
    SHARED = "shared"
    TEAM = "team"
    ORG = "org"


@dataclass
class Tenant:
    """Organization root."""

    id: str
    name: str
    metadata: dict[str, Any]
    created_at: datetime


@dataclass
class Space:
    """Tenant space: private, shared, team, or org."""

    id: str
    tenant_id: str
    kind: SpaceKind
    name: str
    owner_id: str | None
    metadata: dict[str, Any]
    created_at: datetime


class TenantEngine:
    """
    Tenant and space management. Persists to PostgreSQL (metadata store).
    """

    def __init__(self, postgres_uri: str) -> None:
        self._postgres_uri = postgres_uri
        self._session_factory: Any = None

    async def connect(self) -> None:
        """Initialize DB connection."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
            engine = create_async_engine(self._postgres_uri, echo=False)
            self._session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            logger.info("TenantEngine connected")
        except Exception as e:
            logger.error("TenantEngine connection failed: %s", e)
            raise

    async def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Fetch tenant by ID."""
        if self._session_factory is None:
            await self.connect()
        # TODO: Query from DB
        return None

    async def get_space(self, tenant_id: str, space_id: str) -> Space | None:
        """Fetch space by tenant + space ID."""
        if self._session_factory is None:
            await self.connect()
        # TODO: Query from DB
        return None

    async def list_spaces(self, tenant_id: str, kind: SpaceKind | None = None) -> list[Space]:
        """List spaces for tenant, optionally filtered by kind."""
        if self._session_factory is None:
            await self.connect()
        # TODO: Query from DB
        return []

    async def ensure_private_space(self, tenant_id: str, user_id: str) -> Space:
        """Ensure user has a private space; create if missing."""
        if self._session_factory is None:
            await self.connect()
        # TODO: Upsert private space
        return Space(
            id=f"private_{user_id}",
            tenant_id=tenant_id,
            kind=SpaceKind.PRIVATE,
            name="Private",
            owner_id=user_id,
            metadata={},
            created_at=datetime.now(timezone.utc),
        )
