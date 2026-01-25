"""
Observability API — Metrics snapshot, health, traces.

Endpoints:
- GET /observability/metrics/snapshot — metrics snapshot
- GET /observability/health — detailed health
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from src.observability.metrics import MetricsCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/observability", tags=["Observability"])

# Global metrics collector
_metrics = MetricsCollector("kirp")


@router.get("/metrics/snapshot")
async def get_metrics_snapshot() -> dict[str, Any]:
    """
    Get snapshot of KIRP internal metrics.
    Can be consumed by Streamlit or exported to Prometheus.
    """
    # TODO: Collect from MetricsCollector, Elasticsearch, etc.
    return {
        "counters": {},
        "timings": [],
        "last_updated": None,
    }


@router.get("/health")
async def get_health() -> dict[str, Any]:
    """Detailed system health."""
    import os
    health: dict[str, Any] = {
        "status": "healthy",
        "services": {},
    }
    # Check MongoDB
    try:
        from src.core.integrations import get_mongo_client
        client = get_mongo_client()
        if hasattr(client, "admin"):
            client.admin.command("ping")
        health["services"]["mongodb"] = "ok"
    except Exception as e:
        health["services"]["mongodb"] = f"error: {e}"
        health["status"] = "degraded"

    # Check Redis
    try:
        from src.core.integrations import get_redis_client
        r = get_redis_client()
        if r:
            r.ping()
            health["services"]["redis"] = "ok"
    except Exception as e:
        health["services"]["redis"] = f"error: {e}"

    # Check Qdrant
    try:
        import httpx
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{qdrant_url}/collections")
            r.raise_for_status()
            health["services"]["qdrant"] = "ok"
    except Exception as e:
        health["services"]["qdrant"] = f"error: {e}"

    return health
