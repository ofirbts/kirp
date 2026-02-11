"""
V1 Graph API — Unified Knowledge Graph (Life Graph).

GET /api/v1/graph — nodes + edges from SchemaEngine + EventStore.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from src.auth.tenant_context import get_tenant_context
from src.core.graph_engine import GraphBuilder
from src.core.schema_engine import get_schema_engine
from src.main import get_event_store


router = APIRouter(prefix="/api/v1", tags=["V1 Graph"])


@router.get("/graph")
async def get_graph_v1(
    request: Request,
    tenant_id: str = Query("default", description="Tenant ID"),
    space_id: str | None = Query(None, description="Optional space filter"),
    life_area: str | None = Query(None, description="Filter by life area title"),
    project_id: str | None = Query(None, description="Filter by project ID"),
    date_from: str | None = Query(None, description="From date (ISO) for events"),
    date_to: str | None = Query(None, description="To date (ISO) for events"),
    entity_types: str | None = Query(None, description="Comma-separated: task,project,commitment,life_area"),
    source: str | None = Query(None, description="Filter by event source"),
    limit_nodes: int = Query(2000, ge=1, le=5000, description="Max nodes"),
) -> dict[str, Any]:
    """
    Get unified graph (nodes + edges) from schema nodes and events.
    Tenant/space from JWT. Optional filters: life_area, project_id, date range, entity_types, source.
    """
    ctx = get_tenant_context(request)
    tid = ctx.tenant_id
    sid = space_id or ctx.space_id or "all"
    schema = await get_schema_engine()
    store = await get_event_store()
    builder = GraphBuilder(schema, store)
    entity_list = None
    if entity_types:
        entity_list = [x.strip() for x in entity_types.split(",") if x.strip()]
    graph = await builder.build(
        tenant_id=tid,
        space_id=sid,
        life_area=life_area,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
        entity_types=entity_list,
        source_filter=source,
        limit_nodes=limit_nodes,
    )
    out = graph.to_dict()
    out["stats"] = {"node_count": len(graph.nodes), "edge_count": len(graph.edges)}
    return out
