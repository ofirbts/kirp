"""
KIRP integration: handle KIRP events for Brand OS v3.
Routes: brand_os_run_started, agent_completed, gatekeeper_decision, run_completed, run_failed.
"""

from typing import Any, Optional

from brand_os_sdk.orchestrator import run_orchestrator

# Event type strings we handle
BRAND_OS_RUN_STARTED = "brand_os_run_started"
BRAND_OS_WORKFLOW_STARTED = "brand_os_v3.workflow.started"
AGENT_COMPLETED = "agent_completed"
GATEKEEPER_DECISION = "gatekeeper_decision"
RUN_COMPLETED = "run_completed"
RUN_FAILED = "run_failed"


def handle_kirp_event(event: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Route a KIRP event and return a result when applicable.
    - brand_os_run_started / brand_os_v3.workflow.started: run orchestrator, return final_output_format.
    - agent_completed, gatekeeper_decision, run_completed: acknowledge (return small ack or None).
    - run_failed: acknowledge (return None).
    """
    if not event or not isinstance(event, dict):
        return None

    event_type = event.get("event_type") or event.get("type") or event.get("event")
    payload = event.get("payload") or event

    if event_type in (BRAND_OS_RUN_STARTED, BRAND_OS_WORKFLOW_STARTED):
        return _handle_run_started(payload)
    if event_type == AGENT_COMPLETED:
        return _handle_agent_completed(payload)
    if event_type == GATEKEEPER_DECISION:
        return _handle_gatekeeper_decision(payload)
    if event_type == RUN_COMPLETED:
        return _handle_run_completed(payload)
    if event_type == RUN_FAILED:
        return _handle_run_failed(payload)

    # KIRP agent completion events (e.g. brand_os_v3.context_scanner.completed)
    if isinstance(event_type, str) and event_type.startswith("brand_os_v3.") and event_type.endswith(".completed"):
        return _handle_agent_completed(payload)
    if isinstance(event_type, str) and event_type in (
        "brand_os_v3.identity.rejected",
        "brand_os_v3.cto.rejected",
    ):
        return _handle_gatekeeper_decision(payload)
    if isinstance(event_type, str) and event_type == "brand_os_v3.workflow.completed":
        return _handle_run_completed(payload)

    return None


def _handle_run_started(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Run orchestrator and return final_output_format."""
    tenant_id = payload.get("tenant_id")
    platform = payload.get("platform")
    topic_hint = payload.get("topic_hint")
    if not all([tenant_id, platform, topic_hint]):
        return None
    input_payload = {
        "tenant_id": tenant_id,
        "platform": platform,
        "topic_hint": topic_hint,
    }
    if payload.get("trace_id") is not None:
        input_payload["trace_id"] = payload["trace_id"]
    if payload.get("extra_context") is not None:
        input_payload["extra_context"] = payload["extra_context"]
    try:
        return run_orchestrator(input_payload)
    except Exception:
        return None


def _handle_agent_completed(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Acknowledge agent step (no side effect; optional ack)."""
    return {"ack": True, "route": "agent_completed", "trace_id": payload.get("trace_id")}


def _handle_gatekeeper_decision(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Acknowledge gatekeeper decision (no side effect; optional ack)."""
    return {"ack": True, "route": "gatekeeper_decision", "trace_id": payload.get("trace_id")}


def _handle_run_completed(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Acknowledge run completed (no side effect; optional ack)."""
    return {"ack": True, "route": "run_completed", "trace_id": payload.get("trace_id")}


def _handle_run_failed(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Acknowledge run failed (no side effect)."""
    return {"ack": True, "route": "run_failed", "trace_id": payload.get("trace_id")}
