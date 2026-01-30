"""
Read-only Workflows service.

Phase 4.2: exposes list/get functionality. For now it returns empty
collections; later phases will back it with Postgres models and projections.
"""

from __future__ import annotations

from typing import List, Optional

from src.schemas.api_models import Workflow, WorkflowRun


async def list_workflows() -> List[Workflow]:
    """List all workflows. Phase 4.2: returns an empty list."""
    return []


async def get_workflow(workflow_id: str) -> Optional[Workflow]:
    """Get a single workflow by ID. Phase 4.2: returns None."""
    return None


async def list_workflow_runs(
    workflow_id: str,
    status: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
) -> List[WorkflowRun]:
    """List runs for a workflow. Phase 4.2: returns an empty list."""
    return []

