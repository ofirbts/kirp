"""
Kafka wire envelope — single definition for producer JSON and consumer flattening.

Shape on the wire: ``type``, ``data``, ``tenant_id``, ``space_id``, ``user_id``,
plus optional run-envelope fields at the top level (mirrored into merged event data).
"""

from __future__ import annotations

from typing import Any


def build_kafka_emit_dict(
    *,
    event_type: str,
    data: dict[str, Any],
    tenant_id: str,
    space_id: str,
    user_id: str,
    run_id: str | None = None,
    workflow_type: str | None = None,
    trace_id: str | None = None,
    idempotency_key: str | None = None,
    parent_run_id: str | None = None,
) -> dict[str, Any]:
    """Build the JSON-serializable object produced to ``kirp-events`` (matches historical field names)."""
    return {
        "type": event_type,
        "data": data,
        "tenant_id": tenant_id,
        "space_id": space_id,
        "user_id": user_id,
        "run_id": run_id,
        "workflow_type": workflow_type,
        "trace_id": trace_id,
        "idempotency_key": idempotency_key,
        "parent_run_id": parent_run_id,
    }


def flatten_kafka_envelope_to_event_data(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Merge top-level envelope fields into inner ``data`` for ingest/registry dispatch.

    Top-level values win when present (not None); otherwise inner ``data`` supplies them.
    This must stay aligned with multi-tenant rules: no implicit defaults here.
    """
    raw_data = payload.get("data") or {}
    if not isinstance(raw_data, dict):
        raw_data = {}

    def _coalesce_top(key: str) -> Any:
        top = payload.get(key)
        if top is not None:
            return top
        return raw_data.get(key)

    tenant_id = _coalesce_top("tenant_id")
    space_id = _coalesce_top("space_id")
    user_id = _coalesce_top("user_id")

    return {
        **raw_data,
        "tenant_id": tenant_id,
        "space_id": space_id,
        "user_id": user_id,
        # Run-envelope fields: top-level wins when truthy (matches legacy ``or`` merge)
        "run_id": payload.get("run_id") or raw_data.get("run_id"),
        "workflow_type": payload.get("workflow_type") or raw_data.get("workflow_type"),
        "trace_id": payload.get("trace_id") or raw_data.get("trace_id"),
        "idempotency_key": payload.get("idempotency_key") or raw_data.get("idempotency_key"),
        "parent_run_id": payload.get("parent_run_id") or raw_data.get("parent_run_id"),
    }


def validate_ingest_tenant_context(data: dict[str, Any]) -> str | None:
    """Return an error code string if ingest cannot proceed; None if OK."""
    tenant_id = data.get("tenant_id")
    if not tenant_id or tenant_id == "*":
        return "invalid_tenant"
    if not data.get("user_id"):
        return "missing_user_id"
    return None
