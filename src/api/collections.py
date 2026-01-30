"""
Collections API — minimal JSON endpoints for the frontend.

Backs:
- GET  /api/collections
- POST /api/collections/{collection_id}/search
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.schemas.api_models import CollectionsListResponse, VectorSearchResponse
from src.services import collections_service


router = APIRouter(prefix="/api/collections", tags=["Collections"])


@router.get("", response_model=CollectionsListResponse)
async def list_collections(
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> CollectionsListResponse:
    """List collections (read-only, backed by service layer). Tenant context required but not yet used for filtering."""
    collections = await collections_service.list_collections()
    return CollectionsListResponse(data=collections, meta={})


@router.post("/{collection_id}/search", response_model=VectorSearchResponse)
async def vector_search(
    collection_id: str,
    body: dict[str, Any] = Body(...),
) -> VectorSearchResponse:
    """Vector search (read-only, backed by service layer)."""
    results = await collections_service.vector_search(collection_id=collection_id, query=body)
    return VectorSearchResponse(data=results, meta={})

