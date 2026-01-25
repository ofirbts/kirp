# app/main.py
"""
KIRP Unified API Gateway
Production-ready FastAPI application
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import uvicorn

from app.core.persistence import PersistenceManager

# Routers
from app.api import (
    auth, auth_google, query, health, ingest,
    ingest_batch, protected, sources, agents,
    insights, improvements, jobs_extra,
    self_improving, streams,
    webhooks_whatsapp, webhooks_twilio
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIRP-API")


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Startup & shutdown lifecycle"""
    try:
        await PersistenceManager.initialize()
        logger.info("🚀 KIRP OS Booted")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

    yield

    logger.info("🛑 KIRP OS shutdown")


app = FastAPI(
    title="KIRP OS",
    version="7.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(auth_google.router, prefix="/auth/google", tags=["Auth"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(ingest_batch.router, prefix="/ingest/batch", tags=["Ingest"])
app.include_router(protected.router, prefix="/protected", tags=["Protected"])
app.include_router(sources.router, prefix="/sources", tags=["Sources"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(insights.router, prefix="/insights", tags=["Insights"])
app.include_router(improvements.router, prefix="/improvements", tags=["Improvements"])
app.include_router(jobs_extra.router, prefix="/jobs", tags=["Jobs"])
app.include_router(self_improving.router, prefix="/self-improving", tags=["Self-Improving"])
app.include_router(streams.router, prefix="/streams", tags=["Streams"])
app.include_router(webhooks_whatsapp.router, prefix="/webhooks/whatsapp", tags=["WhatsApp"])
app.include_router(webhooks_twilio.router, prefix="/webhooks/twilio", tags=["Twilio"])


@app.get("/dashboard/summary/{user_id}")
async def dashboard_summary(user_id: str):
    return {
        "knowledge_items": 1234,
        "active_jobs": 5,
        "new_insights": 23,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/agent/query")
async def agent_query(payload: dict):
    text = payload.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text")

    return {
        "answer": f"KIRP processed: {text[:50]}...",
        "success": True,
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
