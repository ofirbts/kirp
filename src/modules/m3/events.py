"""
M3 IdentityOS — Event types and payload conventions.

All M3 events use event_type in the form m3.<name> and metadata.module = "m3".
Compatible with KIRP CanonicalEvent (event_type + metadata).
"""

from __future__ import annotations

from typing import Any

# Module tag for governance and filtering
M3_MODULE_TAG = "m3"

# Event type constants (spec section 3.1)
EVENT_M3_IDENTITY_INTENT_DECLARED = "m3.identity_intent_declared"
EVENT_M3_DAILY_REFLECTION_SUBMITTED = "m3.daily_reflection_submitted"
EVENT_M3_MICRO_ACTION_GENERATED = "m3.micro_action_generated"
EVENT_M3_MICRO_ACTION_COMPLETED = "m3.micro_action_completed"
EVENT_M3_MICRO_ACTION_SNOOZED = "m3.micro_action_snoozed"
EVENT_M3_WEEKLY_SYNTHESIS_REQUESTED = "m3.weekly_synthesis_requested"
EVENT_M3_WEEKLY_SYNTHESIS_GENERATED = "m3.weekly_synthesis_generated"
EVENT_M3_MONTHLY_EVOLUTION_REQUESTED = "m3.monthly_evolution_requested"
EVENT_M3_MONTHLY_EVOLUTION_UPDATED = "m3.monthly_evolution_updated"
EVENT_M3_IDENTITY_VECTOR_UPDATED = "m3.identity_vector_updated"
EVENT_M3_GAP_ANALYSIS_COMPUTED = "m3.gap_analysis_computed"
EVENT_M3_HUMAN_GOVERNANCE_REQUIRED = "m3.human_governance_required"

M3_EVENT_TYPES = (
    EVENT_M3_IDENTITY_INTENT_DECLARED,
    EVENT_M3_DAILY_REFLECTION_SUBMITTED,
    EVENT_M3_MICRO_ACTION_GENERATED,
    EVENT_M3_MICRO_ACTION_COMPLETED,
    EVENT_M3_MICRO_ACTION_SNOOZED,
    EVENT_M3_WEEKLY_SYNTHESIS_REQUESTED,
    EVENT_M3_WEEKLY_SYNTHESIS_GENERATED,
    EVENT_M3_MONTHLY_EVOLUTION_REQUESTED,
    EVENT_M3_MONTHLY_EVOLUTION_UPDATED,
    EVENT_M3_IDENTITY_VECTOR_UPDATED,
    EVENT_M3_GAP_ANALYSIS_COMPUTED,
    EVENT_M3_HUMAN_GOVERNANCE_REQUIRED,
)


def ensure_m3_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Ensure metadata has module = m3 for audit and filtering. Does not mutate input."""
    out = dict(metadata or {})
    out["module"] = M3_MODULE_TAG
    return out


def is_m3_event_type(event_type: str) -> bool:
    """True if event_type is an M3 event."""
    return event_type in M3_EVENT_TYPES or (
        isinstance(event_type, str) and event_type.startswith("m3.")
    )
