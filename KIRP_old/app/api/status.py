# app/api/status.py
"""
KIRP Unified Status API
Production observability + health endpoints
"""
import logging
import time
import requests
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends

from app.core.persistence import PersistenceManager
from app.rag.vector_store import get_vector_store
from app.core.redis_client import get_redis
from app.api.auth import get_current_user
from app.observability.alerts import get_alerts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/status", tags=["Status"])

# --- System State ---
START_TIME = time.time()
STATE: Dict[str, Any] = {
    "ingest_count": 0,
    "query_count": 0,
    "last_ingest": None,
    "last_query": None,
    "last_error": None,
}


def uptime() -> float:
    return round(time.time() - START_TIME, 2)


def check_service(url: str, timeout: float = 2.0) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


@router.get("/", response_model=Dict[str, Any])
async def system_status(current_user: dict = Depends(get_current_user)):
    """
    Enterprise system status with full observability.
    """
    # Vector store
    vector_info = {"loaded": False, "vectors_count": 0}
    try:
        store = get_vector_store()
        vector_info["loaded"] = store is not None
    except Exception as e:
        STATE["last_error"] = {
            "message": f"vector_store_init_failed: {e}",
            "time": datetime.now(timezone.utc).isoformat(),
        }

    # Redis
    try:
        redis = await get_redis()
        redis_info = await redis.info()
        redis_status = {
            "connected": True,
            "memory_used": redis_info.get("used_memory_human", "0B"),
        }
    except Exception:
        redis_status = {"connected": False}

    return {
        "api": "🟢 LIVE",
        "uptime_seconds": uptime(),
        "services": {
            "ui": check_service("http://localhost:8501"),
            "bot": check_service("http://localhost:5000/health"),
            "vector_store": vector_info,
            "redis": redis_status,
        },
        "metrics": {
            "ingest": {
                "count": STATE["ingest_count"],
                "last": STATE["last_ingest"],
            },
            "query": {
                "count": STATE["query_count"],
                "last": STATE["last_query"],
            },
        },
        "last_error": STATE["last_error"],
    }


@router.get("/snapshot")
async def system_snapshot():
    """
    Production snapshot for dashboards.
    """
    alerts = await PersistenceManager.get_pending_improvements()
    return {
        "system": "KIRP OS",
        "stage": "PRODUCTION",
        "alerts_count": len(alerts),
        "alerts": get_alerts(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def mark_ingest():
    STATE["ingest_count"] += 1
    STATE["last_ingest"] = datetime.now(timezone.utc).isoformat()


def mark_query():
    STATE["query_count"] += 1
    STATE["last_query"] = datetime.now(timezone.utc).isoformat()


def mark_error(message: str):
    STATE["last_error"] = {
        "message": message,
        "time": datetime.now(timezone.utc).isoformat(),
    }
