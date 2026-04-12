"""
Reconciliation worker — repair partial ingest runs (history / Qdrant / schema projections).

Scans RunController for aggregate state `partial`, loads the canonical Mongo event via
`metadata.run_id`, and replays failed projections through `EventPipeline.reconcile_run`.
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.run_controller import get_run_controller

logger = logging.getLogger(__name__)


class ReconciliationWorker:
    """Orchestrates batch reconciliation of partial runs."""

    def __init__(self, pipeline: Any) -> None:
        self._pipeline = pipeline

    @classmethod
    async def create(cls) -> "ReconciliationWorker":
        """Build pipeline with the same wiring as Celery ingest tasks."""
        from src.core.pipeline_factory import create_connected_event_pipeline

        pipe = await create_connected_event_pipeline()
        return cls(pipe)

    async def reconcile_partial_runs(self, max_runs: int = 50) -> dict[str, Any]:
        """
        Find runs in aggregate state `partial` and attempt `EventPipeline.reconcile_run` for each.
        """
        rc = get_run_controller()
        ids = await rc.list_run_ids_by_state("partial", limit=max_runs)
        results: list[dict[str, Any]] = []
        for rid in ids:
            try:
                res = await self._pipeline.reconcile_run(rid)
                results.append(res)
            except Exception as e:
                logger.exception("reconcile_run failed for %s: %s", rid, e)
                results.append({"run_id": rid, "error": str(e)})
        return {"processed": len(ids), "results": results}
