"""
Brand OS v3 monitoring — FastAPI + Jinja2 dashboard.
Endpoints: /metrics (JSON), /dashboard (HTML with Chart.js).
Data source: content memory log (brand_os_v3/storage/content_memory_log.jsonl or config 02_Content_Memory_Log schema).
"""

import os
import json
from pathlib import Path
from collections import Counter
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

app = FastAPI(title="Brand OS v3 Monitoring", version="3.0.0")

BASE = Path(os.environ.get("BRAND_OS_V3_PATH", Path(__file__).resolve().parent.parent / "brand_os_v3"))
MEMORY_LOG = BASE / "storage" / "content_memory_log.jsonl"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _load_memory_log() -> list[dict]:
    if not MEMORY_LOG.exists():
        return []
    entries = []
    with open(MEMORY_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


@app.get("/metrics")
def metrics() -> dict:
    entries = _load_memory_log()
    total_runs = len(entries)
    statuses = Counter(e.get("status", "unknown") for e in entries)
    approved = statuses.get("approved", 0)
    rejected_identity = statuses.get("rejected_identity", 0)
    rejected_cto = statuses.get("rejected_cto", 0)
    topic_hints = Counter(e.get("topic_hint", "") for e in entries if e.get("topic_hint"))
    top_hooks = topic_hints.most_common(10)
    platforms = Counter(e.get("platform", "") for e in entries if e.get("platform"))
    return {
        "total_runs": total_runs,
        "approved": approved,
        "rejected_identity": rejected_identity,
        "rejected_cto": rejected_cto,
        "avg_revisions": 0.0,
        "top_hooks": [{"topic": k, "count": v} for k, v in top_hooks],
        "top_pillars": [{"platform": k, "count": v} for k, v in platforms.most_common(5)],
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    m = metrics()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "metrics": m},
    )
