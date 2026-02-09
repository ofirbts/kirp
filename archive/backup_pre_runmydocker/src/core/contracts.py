"""
Data contracts & schema governance for KIRP Enterprise.

Exposes JSON Schemas for key API models so external systems can rely on
stable, versioned contracts.
"""

from __future__ import annotations

from typing import Any, Dict

from src.schemas import api_models


def get_contracts() -> Dict[str, Any]:
    """
    Return JSON Schemas for public API models, grouped under a versioned root.

    This is intentionally minimal: it uses Pydantic's json_schema generation
    and does not write to disk. Callers (e.g. observability API) can expose
    this as a contract endpoint.
    """
    models = {
        "Agent": api_models.Agent,
        "Event": api_models.Event,
        "Workflow": api_models.Workflow,
        "WorkflowRun": api_models.WorkflowRun,
        "Task": api_models.Task,
        "Tenant": api_models.Tenant,
        "Space": api_models.Space,
        "User": api_models.User,
        "Role": api_models.Role,
        "Policy": api_models.Policy,
        "AuditEntry": api_models.AuditEntry,
        "GraphNode": api_models.GraphNode,
        "GraphEdge": api_models.GraphEdge,
    }
    return {
        "version": api_models.API_SCHEMA_VERSION,
        "models": {
            name: model.model_json_schema()
            for name, model in models.items()
        },
    }

