"""
RAG API — query feedback and evaluation hooks.

Endpoints:
- POST /api/rag/feedback — record user feedback on RAG results
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.core.config import get_settings
from src.core.event_store import Event, EventStore, Sensitivity
from src.core.governance import GovernanceEngine


router = APIRouter(prefix="/api/rag", tags=["RAG"])

_event_store: EventStore | None = None
_governance: GovernanceEngine | None = None


async def get_rag_event_store() -> EventStore:
    """
    Lightweight EventStore provider for the RAG API to avoid importing from src.main.

    Mirrors the configuration used by the main application.
    """
    global _event_store
    if _event_store is None:
        settings = get_settings()
        _event_store = EventStore(settings.mongo_uri)
        await _event_store.connect()
    return _event_store


async def get_rag_governance() -> GovernanceEngine:
    """
    Lightweight GovernanceEngine provider for the RAG API to avoid import cycles.
    """
    global _governance
    if _governance is None:
        settings = get_settings()
        _governance = GovernanceEngine(settings.opa_url)
        await _governance.connect()
    return _governance


class RagFeedbackIn(BaseModel):
    query: str = Field(..., description="The original user query text.")
    resultId: Optional[str] = Field(
        default=None,
        description="ID of the result/document the feedback refers to (if applicable).",
    )
    rating: Literal["positive", "negative", "neutral"] = Field(
        ...,
        description="User-assigned relevance rating for the result or answer.",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional free-text explanation for the rating.",
    )
    labels: Optional[List[str]] = Field(
        default=None,
        description="Optional tags (e.g. 'hallucination', 'outdated', 'security-concern').",
    )


@router.post("/feedback")
async def submit_rag_feedback(
    body: RagFeedbackIn,
    ctx: TenantContext = Depends(get_effective_tenant_context),
    store: EventStore = Depends(get_rag_event_store),
) -> dict[str, Any]:
    """
    Record user feedback about a RAG result as an event.

    Feedback is stored as an `event_type='rag_feedback'` in the EventStore and
    mirrored into the audit trail via GovernanceEngine.
    """
    from src.core.governance import GovernanceEngine

    # Create feedback event in EventStore (event-sourced feedback loop)
    feedback_event = Event(
        id=uuid4(),
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "",
        user_id=ctx.user_id or "unknown",
        source="rag_feedback",
        content=body.query[:512],
        metadata={
            "rating": body.rating,
            "result_id": body.resultId,
            "labels": body.labels or [],
            "reason": body.reason,
        },
        embedding=[],
        timestamp=datetime.now(timezone.utc),
        sensitivity=Sensitivity.PRIVATE,
        event_type="rag_feedback",
        trace_id=None,
    )
    await store.ingest(feedback_event)

    # Mirror to audit log via GovernanceEngine (for explainability/compliance)
    gov: GovernanceEngine = await get_rag_governance()
    try:
        await gov.log_audit(
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id or "unknown",
            action="rag_feedback",
            resource="rag",
            result="recorded",
            details={
                "feedback_event_id": str(feedback_event.id),
                "rating": body.rating,
                "labels": body.labels or [],
            },
        )
    except Exception:
        # Audit failures should not break user-facing feedback.
        pass

    return {"ok": True}

