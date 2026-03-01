"""
M3 IdentityOS — API routes under /api/v1/m3.

POST /m3/reflect, /m3/synthesis, /m3/evolution create M3 events and run the pipeline.
GET endpoints return data from M3 memory (tenant/user scoped).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.models.event import CanonicalEvent
from src.core.event_registry import get_event_registry
from src.modules.m3.events import (
    ensure_m3_metadata,
    EVENT_M3_DAILY_REFLECTION_SUBMITTED,
    EVENT_M3_WEEKLY_SYNTHESIS_REQUESTED,
    EVENT_M3_MONTHLY_EVOLUTION_REQUESTED,
)
from src.modules.m3.memory import get_m3_memory_store


router = APIRouter(prefix="/api/v1", tags=["M3"])


def _canonical_m3_event(
    ctx: TenantContext,
    event_type: str,
    source: str,
    content: str = "",
    metadata: dict[str, Any] | None = None,
) -> CanonicalEvent:
    """Build a CanonicalEvent for M3 with tenant/space/user from context."""
    meta = ensure_m3_metadata(metadata or {})
    return CanonicalEvent(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id or "all",
        user_id=ctx.user_id,
        source=source,
        trace_id=None,
        parent_event_id=None,
        version=1,
        event_type=event_type,
        content=content,
        metadata=meta,
        agent_id=None,
        input={},
    )


@router.post("/m3/reflect", status_code=201)
async def m3_reflect(
    body: dict[str, Any] | None = None,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> dict[str, Any]:
    """
    Submit a daily reflection. Creates m3.daily_reflection_submitted and runs pipeline.
    Body: reflection_text, pillar_scores (optional), mood (optional), duration_sec (optional), reflection_date (optional).
    """
    payload = body or {}
    reflection_text = payload.get("reflection_text", "")
    reflection_date = payload.get("reflection_date") or date.today().isoformat()
    meta = {
        "reflection_text": reflection_text,
        "pillar_scores": payload.get("pillar_scores") or {},
        "mood": payload.get("mood", ""),
        "duration_sec": payload.get("duration_sec"),
        "reflection_date": reflection_date,
    }
    event = _canonical_m3_event(
        ctx,
        EVENT_M3_DAILY_REFLECTION_SUBMITTED,
        "m3_reflect",
        content=reflection_text,
        metadata=meta,
    )
    registry = get_event_registry()
    event_id = await registry.dispatch(event)
    return {"ok": True, "event_id": str(event_id)}


@router.post("/m3/synthesis", status_code=201)
async def m3_synthesis_request(
    body: dict[str, Any] | None = None,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> dict[str, Any]:
    """
    Request weekly synthesis. Creates m3.weekly_synthesis_requested.
    Body: week_start (YYYY-MM-DD), week_end (YYYY-MM-DD) optional.
    """
    payload = body or {}
    event = _canonical_m3_event(
        ctx,
        EVENT_M3_WEEKLY_SYNTHESIS_REQUESTED,
        "m3_synthesis",
        metadata={"week_start": payload.get("week_start"), "week_end": payload.get("week_end")},
    )
    registry = get_event_registry()
    event_id = await registry.dispatch(event)
    return {"ok": True, "event_id": str(event_id)}


@router.post("/m3/evolution", status_code=201)
async def m3_evolution_request(
    body: dict[str, Any] | None = None,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> dict[str, Any]:
    """
    Request monthly evolution. Creates m3.monthly_evolution_requested.
    Body: month (YYYY-MM) optional.
    """
    payload = body or {}
    month = payload.get("month") or datetime.now(timezone.utc).strftime("%Y-%m")
    event = _canonical_m3_event(
        ctx,
        EVENT_M3_MONTHLY_EVOLUTION_REQUESTED,
        "m3_evolution",
        metadata={"month": month},
    )
    registry = get_event_registry()
    event_id = await registry.dispatch(event)
    return {"ok": True, "event_id": str(event_id)}


@router.get("/m3/reflections")
async def m3_list_reflections(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """List reflection entries from M3 memory (tenant/user scoped)."""
    store = get_m3_memory_store()
    entries = await store.list_reflections(ctx.tenant_id, ctx.user_id, limit=limit)
    data = [
        {
            "id": e.id,
            "reflection_date": e.reflection_date,
            "reflection_text": e.reflection_text,
            "pillar_scores": e.pillar_scores,
            "mood": e.mood,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]
    return {"data": data, "meta": {"count": len(data)}}


@router.get("/m3/synthesis")
async def m3_list_synthesis(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    limit: int = Query(24, ge=1, le=100),
) -> dict[str, Any]:
    """List weekly syntheses from M3 memory."""
    store = get_m3_memory_store()
    syntheses = await store.list_weekly_syntheses(ctx.tenant_id, ctx.user_id, limit=limit)
    data = [
        {
            "synthesis_id": s.synthesis_id,
            "week_start": s.week_start,
            "week_end": s.week_end,
            "summary": s.summary,
            "pillar_trends": s.pillar_trends,
            "insights": s.insights,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in syntheses
    ]
    return {"data": data, "meta": {"count": len(data)}}


@router.get("/m3/evolution")
async def m3_list_evolution(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    limit: int = Query(12, ge=1, le=60),
) -> dict[str, Any]:
    """List monthly evolutions from M3 memory."""
    store = get_m3_memory_store()
    evolutions = await store.list_monthly_evolutions(ctx.tenant_id, ctx.user_id, limit=limit)
    data = [
        {
            "evolution_id": e.evolution_id,
            "month": e.month,
            "trajectory": e.trajectory,
            "new_goals": e.new_goals,
            "pillar_shifts": e.pillar_shifts,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in evolutions
    ]
    return {"data": data, "meta": {"count": len(data)}}


@router.get("/m3/actions")
async def m3_list_actions(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    status: str | None = Query(None, description="pending | completed | snoozed"),
    limit: int = Query(100, ge=1, le=200),
) -> dict[str, Any]:
    """List micro_actions from M3 memory (tenant/user scoped)."""
    store = get_m3_memory_store()
    actions = await store.list_micro_actions(ctx.tenant_id, ctx.user_id, status=status, limit=limit)
    data = [
        {
            "action_id": a.action_id,
            "title": a.title,
            "pillar": a.pillar,
            "status": a.status,
            "due_by": a.due_by,
            "roi_score": a.roi_score,
            "completed_at": a.completed_at,
            "feedback": a.feedback,
        }
        for a in actions
    ]
    return {"data": data, "meta": {"count": len(data)}}


@router.get("/m3/kpis")
async def m3_kpis(
    ctx: TenantContext = Depends(get_effective_tenant_context),
    days: int = Query(7, ge=1, le=90, description="Window for daily reflection and recall metrics"),
) -> dict[str, Any]:
    """
    M3 KPIs per spec 10: Recall Retention, Gap Closure, Identity Alignment, Daily Reflection Completion.
    All derived from M3 memory; explanation path for audit.
    """
    store = get_m3_memory_store()
    from datetime import timedelta
    today = date.today()
    start = today - timedelta(days=days)

    # Daily Reflection Completion: count per day, target = 1/day
    reflections = await store.list_reflections(ctx.tenant_id, ctx.user_id, limit=days * 2)
    by_date: dict[str, int] = {}
    for r in reflections:
        d = r.reflection_date
        if d and d >= start.isoformat() and d <= today.isoformat():
            by_date[d] = by_date.get(d, 0) + 1
    daily_dates = sorted(by_date.keys())
    daily_reflection = {
        "days_with_reflection": len(by_date),
        "total_reflections": sum(by_date.values()),
        "target_met_days": sum(1 for d in daily_dates if by_date.get(d, 0) >= 1),
        "window_days": days,
        "explanation": "Count of m3.daily_reflection_submitted per day from reflection_entries",
    }

    # Recall Retention: % micro_actions completed or snoozed (within window)
    all_actions = await store.list_micro_actions(ctx.tenant_id, ctx.user_id, limit=500)
    completed_or_snoozed = [a for a in all_actions if a.status in ("completed", "snoozed")]
    total = len(all_actions)
    recall_retention = {
        "completed_or_snoozed_count": len(completed_or_snoozed),
        "total_actions": total,
        "rate_pct": round(100.0 * len(completed_or_snoozed) / total, 2) if total else 0.0,
        "explanation": "From m3.micro_action_completed / m3.micro_action_snoozed vs total micro_actions in memory",
    }

    # Identity Alignment: from identity_profiles (pillar_scores as proxy when no alignment_score stored)
    profile = await store.get_identity_profile(ctx.tenant_id, ctx.user_id)
    identity_alignment = {
        "has_profile": profile is not None,
        "pillar_scores": profile.pillar_scores if profile else {},
        "explanation": "From identity_profiles; alignment_score from m3.identity_vector_updated when stored",
    }

    # Gap Closure: trend from gap_analysis events; we don't store snapshots yet
    gap_closure = {
        "value": None,
        "explanation": "Delta in gap_heatmap over time; derive from m3.gap_analysis_computed event store snapshots for trend",
    }

    return {
        "data": {
            "daily_reflection_completion": daily_reflection,
            "recall_retention": recall_retention,
            "identity_alignment": identity_alignment,
            "gap_closure": gap_closure,
        },
        "meta": {"tenant_id": ctx.tenant_id, "user_id": ctx.user_id, "window_days": days},
    }
