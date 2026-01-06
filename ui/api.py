# ui/api.py - גרסה סופית
import requests
from typing import Dict, List, Any
import time

BASE_URL = "http://127.0.0.1:8000"

def safe_request(url: str, method: str = "GET", **kwargs):
    try:
        if method.upper() == "GET":
            resp = requests.get(url, timeout=10)
        else:
            resp = requests.post(url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API {method} {url}: {e}")

def get_health() -> Dict[str, Any]:
    return safe_request(f"{BASE_URL}/health/")

def ingest(text: str) -> Dict[str, Any]:
    return safe_request(
        f"{BASE_URL}/ingest/",
        "POST",
        json={"content": text.strip(), "source": "ui", "timestamp": time.time()}
    )

def ask(question: str) -> Dict[str, Any]:
    return safe_request(  # ← /agent/ במקום /query/
        f"{BASE_URL}/agent/",  # 🔥 תיקון הנתיב!
        "POST",
        json={"question": question.strip()}
    )

def get_tasks() -> List[Dict[str, Any]]:
    return safe_request(f"{BASE_URL}/tasks/")

def weekly_summary() -> Dict[str, Any]:
    return safe_request(f"{BASE_URL}/intelligence/weekly-summary", "POST")
