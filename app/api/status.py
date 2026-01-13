from fastapi import APIRouter
from time import time
from app.rag.vector_store import debug_info
import requests
from typing import Optional
from datetime import datetime, timezone
from app.observability.alerts import get_alerts

router = APIRouter(tags=["Status"])

# --- System State ---
START_TIME = time()
STATE = {
    "last_ingest": None,
    "last_query": None,
    "last_error": None,
    "ingest_count": 0,
    "query_count": 0,
}

def uptime():
    return round(time() - START_TIME, 2)

def check_service(url):
    try:
        r = requests.get(url, timeout=1)
        return r.status_code == 200
    except:
        return False

@router.get("/")
async def system_status():
    vector = debug_info()

    return {
        "api": "live",
        "uptime_seconds": uptime(),

        # External services
        "ui_live": check_service("http://localhost:8501"),
        "bot_live": check_service("http://localhost:5000/health"),

        # Vector store
        "vector_store": {
            "loaded": vector.get("ram_loaded"),
            "disk_exists": vector.get("disk_exists"),
            "vectors_count": vector.get("vectors_count_ram", 0),
        },

        # Ingest / Query
        "ingest": {
            "count": STATE["ingest_count"],
            "last": STATE["last_ingest"],
        },
        "query": {
            "count": STATE["query_count"],
            "last": STATE["last_query"],
        },

        # Errors
        "last_error": STATE["last_error"],
    }

# --- STAGE 50 Snapshot ---
@router.get("/snapshot")
def product_snapshot():
    return {
        "system": "KIRP",
        "stage": 50,
        "alerts": get_alerts(),
    }

def mark_ingest():
    STATE["ingest_count"] += 1
    STATE["last_ingest"] = datetime.now(timezone.utc).isoformat()

def mark_query():
    STATE["query_count"] += 1
    STATE["last_query"] = datetime.now(timezone.utc).isoformat()

def mark_error(msg: str):
    STATE["last_error"] = {
        "message": msg,
        "time": datetime.now(timezone.utc).isoformat()
    }
