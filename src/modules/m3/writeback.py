"""
M3 IdentityOS — Stage 9 writeback: update M3 Typed Memory after pipeline run.

Per spec 4: Reflection & Memory Writeback updates reflection_entries, identity_profiles,
weekly_synthesis, monthly_evolution, micro_actions by event_type.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.modules.m3.events import (
    EVENT_M3_DAILY_REFLECTION_SUBMITTED,
    EVENT_M3_MICRO_ACTION_GENERATED,
    EVENT_M3_MICRO_ACTION_COMPLETED,
    EVENT_M3_MICRO_ACTION_SNOOZED,
    EVENT_M3_WEEKLY_SYNTHESIS_GENERATED,
    EVENT_M3_MONTHLY_EVOLUTION_UPDATED,
    EVENT_M3_IDENTITY_VECTOR_UPDATED,
)
from src.modules.m3.memory import get_m3_memory_store

logger = logging.getLogger(__name__)


async def m3_memory_writeback(
    event_type: str,
    tenant_id: str,
    space_id: str,
    user_id: str,
    event_id: UUID,
    metadata: dict[str, Any],
    content: str = "",
) -> None:
    """
    After pipeline stores the event, write to M3 Typed Memory (reflection_entries,
    micro_actions, weekly_synthesis, monthly_evolution, identity_profiles) per event_type.
    """
    store = get_m3_memory_store()
    meta = metadata or {}
    source_event_id = str(event_id)

    try:
        if event_type == EVENT_M3_DAILY_REFLECTION_SUBMITTED:
            reflection_date = meta.get("reflection_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await store.append_reflection(
                tenant_id=tenant_id,
                user_id=user_id,
                space_id=space_id,
                reflection_date=reflection_date,
                reflection_text=content or meta.get("reflection_text", ""),
                pillar_scores=meta.get("pillar_scores") or {},
                mood=meta.get("mood", ""),
                source_event_id=source_event_id,
            )
            logger.info("M3 writeback: reflection_entries appended for event %s", event_id)

        elif event_type == EVENT_M3_MICRO_ACTION_GENERATED:
            action_id = meta.get("action_id") or source_event_id
            await store.upsert_micro_action(
                tenant_id=tenant_id,
                user_id=user_id,
                space_id=space_id,
                action_id=action_id,
                title=meta.get("title", ""),
                pillar=meta.get("pillar", ""),
                status="pending",
                due_by=meta.get("due_by"),
                roi_score=float(meta.get("roi_score", 0)),
                source_event_id=source_event_id,
            )
            logger.info("M3 writeback: micro_action upserted %s", action_id)

        elif event_type == EVENT_M3_MICRO_ACTION_COMPLETED:
            action_id = meta.get("action_id")
            if action_id:
                completed_at = meta.get("completed_at") or datetime.now(timezone.utc).isoformat()
                await store.upsert_micro_action(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    space_id=space_id,
                    action_id=action_id,
                    title=meta.get("title", ""),
                    pillar=meta.get("pillar", ""),
                    status="completed",
                    due_by=meta.get("due_by"),
                    roi_score=float(meta.get("roi_score", 0)),
                    source_event_id=source_event_id,
                    completed_at=completed_at if isinstance(completed_at, str) else None,
                    feedback=meta.get("feedback", ""),
                )
                logger.info("M3 writeback: micro_action completed %s", action_id)

        elif event_type == EVENT_M3_MICRO_ACTION_SNOOZED:
            action_id = meta.get("action_id")
            if action_id:
                await store.upsert_micro_action(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    space_id=space_id,
                    action_id=action_id,
                    title=meta.get("title", ""),
                    pillar=meta.get("pillar", ""),
                    status="snoozed",
                    due_by=meta.get("snooze_until"),
                    roi_score=float(meta.get("roi_score", 0)),
                    source_event_id=source_event_id,
                )
                logger.info("M3 writeback: micro_action snoozed %s", action_id)

        elif event_type == EVENT_M3_WEEKLY_SYNTHESIS_GENERATED:
            synthesis_id = meta.get("synthesis_id") or source_event_id
            week_start = meta.get("week_start") or ""
            week_end = meta.get("week_end") or ""
            await store.append_weekly_synthesis(
                tenant_id=tenant_id,
                user_id=user_id,
                space_id=space_id,
                synthesis_id=synthesis_id,
                week_start=week_start,
                week_end=week_end,
                summary=content or meta.get("summary", ""),
                pillar_trends=meta.get("pillar_trends") or {},
                insights=meta.get("insights") or [],
                source_event_id=source_event_id,
            )
            logger.info("M3 writeback: weekly_synthesis appended %s", synthesis_id)

        elif event_type == EVENT_M3_MONTHLY_EVOLUTION_UPDATED:
            evolution_id = meta.get("evolution_id") or source_event_id
            month = meta.get("month") or datetime.now(timezone.utc).strftime("%Y-%m")
            await store.append_monthly_evolution(
                tenant_id=tenant_id,
                user_id=user_id,
                space_id=space_id,
                evolution_id=evolution_id,
                month=month,
                trajectory=meta.get("trajectory") or [],
                new_goals=meta.get("new_goals") or [],
                pillar_shifts=meta.get("pillar_shifts") or {},
                source_event_id=source_event_id,
            )
            logger.info("M3 writeback: monthly_evolution appended %s", evolution_id)

        elif event_type == EVENT_M3_IDENTITY_VECTOR_UPDATED:
            vector = meta.get("identity_vector")
            if vector is None and meta.get("pillar_deltas"):
                vector = []
            if vector is not None:
                await store.upsert_identity_profile(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    space_id=space_id,
                    identity_vector=vector if isinstance(vector, list) else [],
                    pillar_scores=meta.get("pillar_deltas") or meta.get("pillar_scores") or {},
                    source_event_id=source_event_id,
                    ideal_self_vector=meta.get("ideal_self_vector"),
                )
                logger.info("M3 writeback: identity_profile updated for user %s", user_id)
    except Exception as e:
        logger.warning("M3 writeback failed (event already stored): %s", e)
