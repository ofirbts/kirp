import app.bootstrap 
import logging
from fastapi import FastAPI, APIRouter, Query, Request
from contextlib import asynccontextmanager

# API Routers
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.ingest_batch import router as ingest_batch_router
from app.api.query import router as query_router
from app.api.query_stream import router as query_stream_router
from app.api.debug import router as debug_router
from app.api.agent import router as agent_router
from app.api.status import router as status_router
from app.api.self_improving import router as self_improving_router
from app.api.agent_query import router as agent_query_router
from app.api.debug_memory import router as debug_memory_router
from app.api.observability import router as observability_router 
from app.api.policy import router as policy_router 
from app.api.webhooks_twilio import router as twilio_router
from app.api.memories import router as memories_router
from app.ui.ui import router as ui_router

# Core components
from app.rag.vector_store import load_vector_store
from app.core.persistence import PersistenceManager
from app.agent.agent import agent
from app.core.state_snapshot import save_snapshot, load_snapshot
from app.core.tenant import TenantContext

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    try:
        load_vector_store()
    except Exception as e:
        logger.error(f"Failed to load vector store: {e}")

    try:
        # עדיפות ל-Snapshot עדכני, ואז ל-PersistenceManager
        state = load_snapshot() or PersistenceManager.load_agent_state()
        if state:
            agent.load_state(state)
    except Exception as e:
        logger.error(f"Failed to load agent state: {e}")

    yield

    # --- Shutdown ---
    try:
        state_data = agent.dump_state()
        PersistenceManager.save_agent_state(state_data)
        save_snapshot(state_data)
    except Exception as e:
        logger.error(f"Failed to save agent state during shutdown: {e}")

app = FastAPI(
    title="KIRP AI Platform",
    lifespan=lifespan,
)

# Global Middleware
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    tenant = request.headers.get("X-Tenant", "default")
    TenantContext.set(tenant)
    return await call_next(request)

# --- Router Registration ---

# Core API
app.include_router(health_router, prefix="/health", tags=["System"])
app.include_router(status_router, prefix="/status", tags=["System"])
app.include_router(observability_router, prefix="/observability", tags=["System"])

# Data & Memory
app.include_router(ingest_router, prefix="/ingest", tags=["Data"])
app.include_router(ingest_batch_router, prefix="/ingest", tags=["Data"])
app.include_router(memories_router, prefix="/memories", tags=["Data"])
app.include_router(debug_memory_router, prefix="/debug/memory", tags=["Debug"])

# Agent & Query
app.include_router(query_router, prefix="/query", tags=["Agent"])
app.include_router(query_stream_router, prefix="/query", tags=["Agent"])
app.include_router(agent_router, prefix="/agent", tags=["Agent"])
app.include_router(agent_query_router, prefix="/agent/query", tags=["Agent"])
app.include_router(self_improving_router, prefix="/agent/self-improve", tags=["Agent"])

# Specialized & Webhooks
app.include_router(policy_router, prefix="/policy", tags=["Governance"])
app.include_router(twilio_router, prefix="/webhooks/twilio", tags=["Webhooks"])
app.include_router(ui_router, prefix="/ui", tags=["UI"])

# Business Logic Placeholders (Tasks & Intelligence)
tasks_router = APIRouter(tags=["Business"], prefix="/tasks")
@tasks_router.get("/")
async def get_tasks():
    return {"tasks": [], "summary": "System Ready"}

intelligence_router = APIRouter(tags=["Business"], prefix="/intelligence")
@intelligence_router.post("/weekly-summary")
async def weekly_summary():
    return {"week": "2026-W02", "status": "Ready"}

app.include_router(tasks_router)
app.include_router(intelligence_router)

@app.get("/")
async def root():
    return {
        "app": "KIRP AI Platform",
        "status": "Running",
        "docs": "/docs"
    }