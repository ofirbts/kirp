"""
Observability API — Metrics snapshot, health, traces.

Endpoints:
- GET /observability/metrics/snapshot — metrics snapshot
- GET /observability/health — detailed health
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.core.contracts import get_contracts
from src.core.event_store import EventStore
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
    
    # Basic snapshot structure; details are populated via Prometheus scraping.
    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "namespaces": ["kirp_http", "kirp_pipeline", "kirp_worker", "kirp_rag"],
    }


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


@router.get("/contracts")
async def get_data_contracts() -> dict[str, Any]:
    """
    Expose versioned JSON Schemas for key API models.

    This acts as a data-contract endpoint for external systems.
    """
    return get_contracts()


@router.get("/health")
async def get_health(
    tenant_id: str | None = Query(None, description="Optional tenant ID for response tagging / correlation"),
) -> dict[str, Any]:
    """Detailed system health with all services. Optionally tag response with tenant_id for per-tenant correlation."""
    import os
    import time
    from datetime import datetime, timezone

    health: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {},
        "checks": {},
    }
    if tenant_id:
        health["tenant_id"] = tenant_id
    
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
        from sqlalchemy import text
        from src.core.integrations import get_postgres_engine
        start = time.time()
        engine = get_postgres_engine()
        if engine:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
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


@router.get("/tenant-analytics")
async def get_tenant_analytics(
    tenant_id: str | None = Query(None, description="Optional tenant filter; empty = all tenants"),
    hours: int = Query(24, ge=1, le=168),
) -> dict[str, Any]:
    """
    Simple multi-tenant analytics over the event store.

    Returns approximate event counts over a recent time window.
    """
    from datetime import datetime, timedelta, timezone
    from motor.motor_asyncio import AsyncIOMotorClient
    import os

    uri = os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin")
    client = AsyncIOMotorClient(uri)
    db = client["kirp"]

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    match_stage: dict[str, Any] = {"timestamp": {"$gte": since}}
    if tenant_id:
        match_stage["tenant_id"] = tenant_id

    pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$tenant_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = await db.events.aggregate(pipeline).to_list(length=100)
    client.close()

    data = [
        {"tenant_id": r["_id"], "event_count": r["count"]}
        for r in rows
    ]
    return {
        "window_hours": hours,
        "tenant_id": tenant_id,
        "data": data,
    }
