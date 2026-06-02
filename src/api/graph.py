"""
Graph API — minimal JSON endpoints for the frontend.

Backs:
- GET /api/graph
- GET /api/graph/nodes/{id}
- GET /api/graph/nodes/{id}/neighbors
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.observability.metrics import MetricsCollector
from src.schemas.api_models import GraphData, GraphResponse
from src.services import graph_service


router = APIRouter(prefix="/api/graph", tags=["Graph"])
_metrics = MetricsCollector("kirp_graph")


@router.get("", response_model=GraphResponse)
async def get_graph(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    nodeType: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
) -> GraphResponse:
    """Get a graph snapshot (read-only, backed by service layer). Tenant/space enforced via JWT context."""
    nodes, edges = await graph_service.get_graph(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id,
        node_type=nodeType,
        from_ts=from_,
        to_ts=to,
    )
    _metrics.inc("requests_total", labels={"tenant_id": ctx.tenant_id})
    return GraphResponse(data=GraphData(nodes=nodes, edges=edges), meta={})


@router.get("/nodes/{node_id}", response_model=GraphResponse)
async def get_graph_node(
    node_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> GraphResponse:
    """Get a single graph node (read-only). Scoped to authenticated tenant."""
    nodes, edges = await graph_service.get_node(node_id, ctx.tenant_id)
    return GraphResponse(data=GraphData(nodes=nodes, edges=edges), meta={})


@router.get("/nodes/{node_id}/neighbors", response_model=GraphResponse)
async def get_graph_node_neighbors(
    node_id: str,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> GraphResponse:
    """Get neighbors for a node (read-only). Scoped to authenticated tenant."""
    nodes, edges = await graph_service.get_neighbors(node_id, ctx.tenant_id)
    return GraphResponse(data=GraphData(nodes=nodes, edges=edges), meta={})

