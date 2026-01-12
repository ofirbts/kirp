import os
import requests
from app.core.persistence import PersistenceManager

def check_qdrant() -> str:
    host = os.getenv("QDRANT_HOST", "localhost")
    try:
        resp = requests.get(f"http://{host}:6333/healthz", timeout=2)
        return "Online" if resp.status_code == 200 else "Error"
    except:
        return "Offline"

def get_full_system_status():
    stats = PersistenceManager.get_system_stats()
    return {
        "Database (Mongo)": stats["mongo_status"],
        "Vector Store (Qdrant)": check_qdrant(),
        "Events Last 24h": stats["daily_events_count"],
        "Environment": os.getenv("ENVIRONMENT", "development")
    }