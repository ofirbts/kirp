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
    from src.observability.metrics import MetricsCollector
    from datetime import datetime, timezone
    
    metrics = MetricsCollector("kirp")
    
    # Collect metrics (if Prometheus available)
    snapshot = {
        "counters": {},
        "gauges": {},
        "histograms": {},
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    
    # In production, this would query Prometheus or metrics store
    # For now, return structure
    return snapshot


@router.get("/metrics/prometheus")
async def get_prometheus_metrics() -> str:
    """
    Export metrics in Prometheus format.
    """
    try:
        from prometheus_client import generate_latest, REGISTRY
        return generate_latest(REGISTRY).decode("utf-8")
    except ImportError:
        return "# Prometheus client not available\n"


@router.get("/health")
async def get_health() -> dict[str, Any]:
    """Detailed system health with all services."""
    import os
    import time
    from datetime import datetime, timezone
    
    health: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {},
        "checks": {},
    }
    
    # Check MongoDB
    try:
        from src.core.integrations import get_mongo_client
        start = time.time()
        client = get_mongo_client()
        if hasattr(client, "admin"):
            client.admin.command("ping")
        latency = time.time() - start
        health["services"]["mongodb"] = {"status": "ok", "latency_ms": latency * 1000}
        health["checks"]["mongodb"] = True
    except Exception as e:
        health["services"]["mongodb"] = {"status": "error", "error": str(e)}
        health["checks"]["mongodb"] = False
        health["status"] = "degraded"

    # Check Redis
    try:
        from src.core.integrations import get_redis_client
        start = time.time()
        r = get_redis_client()
        if r:
            r.ping()
        latency = time.time() - start
        health["services"]["redis"] = {"status": "ok", "latency_ms": latency * 1000}
        health["checks"]["redis"] = True
    except Exception as e:
        health["services"]["redis"] = {"status": "error", "error": str(e)}
        health["checks"]["redis"] = False
        health["status"] = "degraded"

    # Check Qdrant
    try:
        import httpx
        start = time.time()
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{qdrant_url}/collections")
            r.raise_for_status()
        latency = time.time() - start
        health["services"]["qdrant"] = {"status": "ok", "latency_ms": latency * 1000}
        health["checks"]["qdrant"] = True
    except Exception as e:
        health["services"]["qdrant"] = {"status": "error", "error": str(e)}
        health["checks"]["qdrant"] = False
        health["status"] = "degraded"
    
    # Check PostgreSQL
    try:
        from src.core.integrations import get_postgres_engine
        start = time.time()
        engine = get_postgres_engine()
        if engine:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
        latency = time.time() - start
        health["services"]["postgresql"] = {"status": "ok", "latency_ms": latency * 1000}
        health["checks"]["postgresql"] = True
    except Exception as e:
        health["services"]["postgresql"] = {"status": "error", "error": str(e)}
        health["checks"]["postgresql"] = False
        health["status"] = "degraded"
    
    # Check Kafka
    try:
        from src.core.integrations import get_kafka_producer
        start = time.time()
        producer = get_kafka_producer()
        latency = time.time() - start
        health["services"]["kafka"] = {"status": "ok" if producer else "unavailable", "latency_ms": latency * 1000}
        health["checks"]["kafka"] = producer is not None
    except Exception as e:
        health["services"]["kafka"] = {"status": "error", "error": str(e)}
        health["checks"]["kafka"] = False
        health["status"] = "degraded"
    
    # Overall status
    all_checks = all(health["checks"].values())
    if not all_checks:
        health["status"] = "degraded" if any(health["checks"].values()) else "unhealthy"

    return health
