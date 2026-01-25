"""
Schema Structure Agent — Builds schemas: tasks, projects, life areas, categories.
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.agent_framework import AgentSpec, AutonomyLevel
from src.core.schema_engine import SchemaEngine, SchemaEntity, SchemaNode
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def _handler(
    tenant_id: str,
    space_id: str,
    user_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Infer and upsert schema nodes from RAG + events."""
    rag = context.get("rag_response")
    schema_engine: SchemaEngine | None = context.get("schema_engine")
    if not schema_engine:
        return {"ok": False, "error": "missing_schema_engine"}
    # TODO: LLM to extract tasks, projects, life areas from context; upsert via schema_engine
    nodes: list[SchemaNode] = []
    for n in nodes:
        await schema_engine.upsert_node(n)
    return {"ok": True, "nodes_upserted": len(nodes), "explanation": "schema_structure"}


class SchemaStructureAgent:
    """Builds and maintains schemas from events."""

    @staticmethod
    async def run(
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return await _handler(tenant_id, space_id, user_id, context)


schema_structure_spec = AgentSpec(
    name="SchemaStructureAgent",
    type="schema",
    triggers=["ingest", "schema_refresh"],
    tools=["rag", "schema", "llm"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Builds schemas: tasks, projects, life areas, categories.",
    handler=_handler,
)
