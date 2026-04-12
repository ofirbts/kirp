"""
V1 RAG Search API — Multi-tenant RAG endpoint under /api/v1.

Endpoint:
- POST /api/v1/rag/search

Features:
- Uses JWT-based tenant context via get_tenant_context(request)
- Reuses the shared RAGEngine instance from src.main when available
- Enforces tenant/space isolation (tenant_id, space_id, user_id)
- Respects space membership via context_service (allowed_space_ids)
- Supports limit, since, source, multihop (use_multihop), and optional space override
- Production-grade error handling and structured logging
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel, Field, field_validator

from src.core.auth import get_current_user, User
from src.core.jwt_utils import require_auth
from src.core.rag_engine import RAGEngine, RAGResponse
from src.core.config import get_settings
from src.services.context_service import get_accessible_space_ids, can_access_space


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["V1 RAG"])

_local_rag_engine: RAGEngine | None = None


async def _get_rag_engine_for_v1() -> RAGEngine:
    """
    Reuse the shared RAGEngine instance from src.main when possible.

    Falls back to a local singleton configured from Settings when src.main
    is not available (e.g. in certain tooling/test contexts).
    """
    # Try to reuse the main application's RAGEngine (preferred).
    try:
        from src.main import get_rag_engine as _main_get_rag_engine  # type: ignore

        engine = await _main_get_rag_engine()
        if isinstance(engine, RAGEngine):
            return engine
    except Exception as e:
        logger.warning("v1_rag: main.get_rag_engine unavailable, falling back to local engine: %s", e)

    # Local singleton fallback using central Settings.
    global _local_rag_engine
    if _local_rag_engine is None:
        settings = get_settings()
        _local_rag_engine = RAGEngine(
            qdrant_url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            qdrant_api_key=settings.qdrant_api_key,
        )
        await _local_rag_engine.connect()
    return _local_rag_engine


class RagSearchRequest(BaseModel):
    """Request body for POST /api/v1/rag/search."""

    query: str = Field(..., min_length=1, description="Natural language query to search over tenant data.")
    tenant_id: Optional[str] = Field(
        default=None,
        description="Deprecated: ignored for routing. If set and differs from JWT tenant, request is rejected.",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return (1-100).",
    )
    since: Optional[datetime] = Field(
        default=None,
        description="Optional lower bound for event timestamp (ISO 8601).",
    )
    source: Optional[str] = Field(
        default=None,
        description="Optional source filter (e.g. 'slack', 'notion', 'email').",
    )
    multihop: Optional[bool] = Field(
        default=None,
        description="Override default multi-hop behavior. True=force multi-hop; False=single-hop.",
    )
    space_id: Optional[str] = Field(
        default=None,
        description="Optional space override within the tenant (must be accessible to the user).",
    )

    @field_validator("query")
    @classmethod
    def _strip_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be empty")
        return v


class RagSearchHit(BaseModel):
    text: str
    score: float
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    explanation: str
    confidence: float


class RagSearchResponseModel(BaseModel):
    ok: bool
    results: list[RagSearchHit]
    context: str
    confidence: float
    query_scopes: dict[str, Any]


@router.post(
    "/rag/search",
    response_model=RagSearchResponseModel,
    summary="RAG search with multi-tenant isolation",
    tags=["V1 RAG"],
)
async def rag_search_v1(
    body: RagSearchRequest = Body(...),
    _auth_payload: dict[str, Any] = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> RagSearchResponseModel:
    """
    Perform a RAG search over the tenant/space-scoped knowledge base.

    - Tenant and user are derived from JWT via get_current_user.
    - Optional tenant_id/space_id overrides in the body are respected when provided.
    - Optionally restricts results to spaces the user is a member of (allowed_space_ids).
    - Supports multi-hop query expansion and hybrid retrieval.
    """
    # Tenant from JWT only — body.tenant_id cannot override (prevents cross-tenant search).
    body_tid = (body.tenant_id or "").strip() if body.tenant_id is not None else ""
    utid = (user.tenant_id or "").strip()
    if body_tid and body_tid != utid:
        raise HTTPException(status_code=403, detail="tenant mismatch")
    tenant_id = utid
    user_id = (user.id or "").strip()
    if not tenant_id or not user_id:
        raise HTTPException(status_code=400, detail="Authenticated tenant_id and user_id are required for RAG search")

    # Resolve effective space and allowed spaces for membership-aware filtering
    try:
        allowed_space_ids = await get_accessible_space_ids(tenant_id, user_id)
    except Exception as e:
        logger.warning(
            "v1_rag: get_accessible_space_ids failed; falling back to ['all'] (tenant=%s user=%s): %s",
            tenant_id,
            user_id,
            e,
        )
        allowed_space_ids = ["all"]

    effective_space_id = body.space_id or "all"
    if body.space_id and body.space_id.strip() and body.space_id != effective_space_id:
        # Enforce that requested space is actually accessible.
        can_access = await can_access_space(tenant_id, user_id, body.space_id)
        if not can_access:
            raise HTTPException(
                status_code=403,
                detail="Not allowed to access requested space_id for this tenant/user.",
            )
        effective_space_id = body.space_id

    try:
        engine = await _get_rag_engine_for_v1()
    except Exception as e:
        logger.exception("v1_rag: failed to initialize RAGEngine")
        raise HTTPException(status_code=503, detail=f"RAG engine unavailable: {e}") from e

    try:
        logger.info(
            "v1_rag.search start tenant=%s space=%s user=%s limit=%s multihop=%s",
            tenant_id,
            effective_space_id,
            user_id,
            body.limit,
            body.multihop,
        )
        rag_resp: RAGResponse = await engine.search(
            query=body.query,
            tenant_id=tenant_id,
            space_id=effective_space_id,
            user_id=user_id,
            limit=body.limit,
            since=body.since,
            source=body.source,
            use_multihop=body.multihop,
            allowed_space_ids=allowed_space_ids,
        )
        logger.info(
            "v1_rag.search ok tenant=%s space=%s user=%s results=%s confidence=%.3f",
            tenant_id,
            effective_space_id,
            user_id,
            len(rag_resp.results),
            rag_resp.confidence,
        )
    except ValueError as e:
        # Validation / configuration errors from RAGEngine (e.g. missing tenant_id).
        logger.warning(
            "v1_rag.search validation error tenant=%s space=%s user=%s: %s",
            tenant_id,
            effective_space_id,
            user_id,
            e,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception(
            "v1_rag.search failed tenant=%s space=%s user=%s",
            tenant_id,
            effective_space_id,
            user_id,
        )
        raise HTTPException(status_code=500, detail="RAG search failed") from e

    hits: list[RagSearchHit] = [
        RagSearchHit(
            text=r.text,
            score=r.score,
            source=r.source,
            metadata=r.metadata,
            explanation=r.explanation,
            confidence=r.confidence,
        )
        for r in rag_resp.results
    ]

    return RagSearchResponseModel(
        ok=True,
        results=hits,
        context=rag_resp.context_text,
        confidence=rag_resp.confidence,
        query_scopes=rag_resp.query_scopes,
    )

