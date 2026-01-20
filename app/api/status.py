# app/api/status.py
from fastapi import APIRouter
from time import time
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.observability.alerts import get_alerts
from app.rag.vector_store import get_vector_store

router = APIRouter(tags=["Status"])

# --- System State ---
START_TIME = time()
STATE: Dict[str, Any] = {
    "last_ingest": None,
    "last_query": None,
    "last_error": None,
    "ingest_count": 0,
    "query_count": 0,
}

def uptime() -> float:
    return round(time() - START_TIME, 2)

def check_service(url: str) -> bool:
    try:
        r = requests.get(url, timeout=1)
        return r.status_code == 200
    except Exception:
        return False

@router.get("/")
async def system_status():
    # ניסיון עדין לבדוק את ה־Vector Store
    vector_info = {
        "loaded": False,
        "disk_exists": None,
        "vectors_count": None,
    }
    try:
        store = get_vector_store()
        # לא תמיד יש API נוח לספירה, אז נשאיר את זה “רך”
        vector_info["loaded"] = store is not None
    except Exception as e:
        STATE["last_error"] = {
            "message": f"vector_store_init_failed: {e}",
            "time": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "api": "live",
        "uptime_seconds": uptime(),

        # External services
        "ui_live": check_service("http://localhost:8501"),
        "bot_live": check_service("http://localhost:5000/health"),

        # Vector store
        "vector_store": vector_info,

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
