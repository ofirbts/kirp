"""
Reconciliation worker — repair partial ingest runs (history / Qdrant / schema projections).

Scans RunController for aggregate state `partial`, loads the canonical Mongo event via
`metadata.run_id`, and replays failed projections through `EventPipeline.reconcile_run`.
"""

from __future__ import annotations

import logging
import os
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
        from src.core.agent_registry import get_agent_framework_with_all_agents
        from src.core.event_store import EventStore
        from src.core.governance import GovernanceEngine
        from src.core.pipeline import EventPipeline
        from src.core.rag_engine import RAGEngine
        from src.core.schema_engine import SchemaEngine

        store = EventStore(
            os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin")
        )
        await store.connect()
        rag = RAGEngine(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        await rag.connect()
        schema = SchemaEngine(
            os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp")
        )
        await schema.connect()
        gov = GovernanceEngine(os.getenv("OPA_URL"))
        af = get_agent_framework_with_all_agents()
        pipe = EventPipeline(store, rag, schema, gov, af)
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
