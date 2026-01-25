"""
Schema Engine — Tasks, projects, life areas, categories.

Builds and maintains structured schemas from events.
Used by agents (e.g. SchemaStructureAgent) and UI views.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SchemaEntity(str, Enum):
    TASK = "task"
    PROJECT = "project"
    LIFE_AREA = "life_area"
    CATEGORY = "category"


@dataclass
class SchemaNode:
    """Single schema entity (task, project, etc.)."""

    id: str
    entity: SchemaEntity
    tenant_id: str
    space_id: str
    title: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SchemaEngine:
    """
    Manages structured schemas. Metadata stored in PostgreSQL (via repository).
    """

    def __init__(self, postgres_uri: str) -> None:
        self._postgres_uri = postgres_uri
        self._session_factory: Any = None

    async def connect(self) -> None:
        """Initialize SQLAlchemy async engine + session factory."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
            from sqlalchemy.orm import declarative_base
            engine = create_async_engine(self._postgres_uri, echo=False)
            self._session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            logger.info("SchemaEngine connected to PostgreSQL")
        except Exception as e:
            logger.error("SchemaEngine connection failed: %s", e)
            raise

    async def upsert_node(self, node: SchemaNode) -> str:
        """Insert or update a schema node."""
        if self._session_factory is None:
            await self.connect()
        # TODO: SQLAlchemy models + upsert logic
        logger.info("SchemaEngine upsert: %s %s", node.entity.value, node.id)
        return node.id

    async def list_nodes(
        self,
        tenant_id: str,
        space_id: str | None = None,
        entity: SchemaEntity | None = None,
    ) -> list[SchemaNode]:
        """List schema nodes with optional filters."""
        if self._session_factory is None:
            await self.connect()
        # TODO: Query from DB
        return []
