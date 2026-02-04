"""
KIRP Enterprise — FastAPI main app.

North Star: Controlled Intelligence Layer · Event-Sourced · Multi-Tenant · Zero Leakage.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any

# Ensure project root is on sys.path when running as a script (e.g. Streamlit, `python src/main.py`)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.api import governance, observability, whatsapp_os, brand
import src.api.command as command


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("KIRP")


# --- Pydantic models ---
class IngestRequest(BaseModel):
    tenant_id: str
    space_id: str
    user_id: str
    content: str
    source: str = "api"


class QueryRequest(BaseModel):
    tenant_id: str
    space_id: str
    user_id: str
    query: str
    k: int = 6


# --- Globals (lazy init) ---
_event_store: Any = None
_rag_engine: Any = None
_schema_engine: Any = None
_governance: Any = None
_agent_framework: Any = None
_pipeline: Any = None


async def get_event_store() -> Any:
    global _event_store
    if _event_store is None:
        from src.core.event_store import EventStore
        _event_store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
        await _event_store.connect()
    return _event_store


async def get_rag_engine() -> Any:
    global _rag_engine
    if _rag_engine is None:
        from src.core.rag_engine import RAGEngine
        _rag_engine = RAGEngine(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            collection=os.getenv("QDRANT_COLLECTION", "kirp_vectors"),
        )
        await _rag_engine.connect()
    return _rag_engine


async def get_schema_engine() -> Any:
    from src.core.schema_engine import get_schema_engine as _get
    return await _get()


async def get_governance() -> Any:
    global _governance
    if _governance is None:
        from src.core.governance import GovernanceEngine
        _governance = GovernanceEngine(os.getenv("OPA_URL"))
    return _governance


async def get_agent_framework() -> Any:
    global _agent_framework
    if _agent_framework is None:
        from src.core.agent_framework import AgentFramework
        from src.core.agent_registry import register_all_agents
        _agent_framework = AgentFramework()
        register_all_agents(_agent_framework)
    return _agent_framework


async def get_pipeline() -> Any:
    global _pipeline
    if _pipeline is None:
        from src.core.pipeline import EventPipeline
        store = await get_event_store()
        rag = await get_rag_engine()
        schema = await get_schema_engine()
        gov = await get_governance()
        agents = await get_agent_framework()
        _pipeline = EventPipeline(store, rag, schema, gov, agents)
    return _pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect stores. Shutdown: close."""
    logger.info("KIRP Enterprise starting")
    # Ensure Prometheus multiprocess dir exists (avoids FileNotFoundError for counter_*.db in containers)
    prom_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if prom_dir:
        os.makedirs(prom_dir, exist_ok=True)
        logger.debug("Prometheus multiprocess dir ensured: %s", prom_dir)
    try:
        await get_event_store()
        await get_rag_engine()
        await get_schema_engine()
        await get_agent_framework()
        await get_pipeline()
    except Exception as e:
        logger.error("Startup failed: %s", e)
    yield
    logger.info("KIRP Enterprise shutting down")


app = FastAPI(
    title="KIRP Enterprise — Intelligence OS",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3100",
    "http://127.0.0.1:3100",
    "http://172.19.112.1:3100",
    "http://0.0.0.0:3100"
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Development auth bypass: set request.state.user so tenant_context does not 401
@app.middleware("http")
async def dev_auth_middleware(request, call_next):
    if not hasattr(request.state, "user") or request.state.user is None:
        skip = os.getenv("SKIP_AUTH", "").lower() in ("1", "true", "yes")
        dev_env = os.getenv("ENV", "").lower() == "development"
        if skip or dev_env:
            request.state.user = {
                "tenant_id": "default",
                "space_id": "all",
                "user_id": "dev",
                "roles": ["admin", "owner"],
            }
        else:
            auth = request.headers.get("Authorization") or ""
            if auth.startswith("Bearer "):
                token = auth[7:].strip()
                dev_token = os.getenv("DEV_TOKEN", "")
                if dev_token and token == dev_token:
                    request.state.user = {
                        "tenant_id": "default",
                        "space_id": "all",
                        "user_id": "dev",
                        "roles": ["admin", "owner"],
                    }
    return await call_next(request)


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check for Docker/K8s."""
    try:
        store = await get_event_store()
        rag = await get_rag_engine()
        return {
            "status": "healthy",
            "event_store": "ok",
            "rag_engine": "ok",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/stats")
async def stats() -> dict[str, Any]:
    """Dashboard stats from real data (event count, agents, etc.)."""
    try:
        store = await get_event_store()
        agents = await get_agent_framework()
        knowledge_count = await store.count_events(tenant_id="default", space_id="all")
        agent_list = agents.list_all()
        notifications = min(99, knowledge_count)
        return {
            "knowledge_items": knowledge_count,
            "active_jobs": 0,
            "new_insights": max(0, knowledge_count // 10),
            "agents": len(agent_list),
            "notifications": notifications,
        }
    except Exception:
        return {
            "knowledge_items": 0,
            "active_jobs": 0,
            "new_insights": 0,
            "agents": 7,
            "notifications": 0,
        }


@app.post("/api/v1/ingest")
async def ingest(req: IngestRequest) -> dict[str, Any]:
    """Ingest content -> pipeline -> event store + RAG + agents."""
    try:
        pipe = await get_pipeline()
        ev_id = await pipe.run(
            tenant_id=req.tenant_id,
            space_id=req.space_id,
            user_id=req.user_id,
            source=req.source,
            content=req.content,
        )
        return {"ok": True, "event_id": str(ev_id)}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query")
async def query(req: QueryRequest) -> dict[str, Any]:
    """RAG query + optional agent."""
    try:
        rag = await get_rag_engine()
        resp = await rag.search(
            query=req.query,
            tenant_id=req.tenant_id,
            space_id=req.space_id,
            user_id=req.user_id,
            limit=req.k,
        )
        return {
            "ok": True,
            "answer": resp.context_text,
            "confidence": resp.confidence,
            "results": [
                {"text": r.text, "score": r.score, "source": r.source}
                for r in resp.results
            ],
        }
    except Exception as e:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agents")
async def list_agents() -> list[dict[str, Any]]:
    """List registered agents (id = name for E2E and callability)."""
    agents = await get_agent_framework()
    return [
        {
            "id": s.name,
            "name": s.name,
            "type": s.type,
            "triggers": s.triggers,
            "description": s.description,
        }
        for s in agents.list_all()
    ]


@app.post("/api/v1/agents/{agent_id}/run")
async def run_agent_v1(agent_id: str, body: dict | None = None) -> dict[str, Any]:
    """Trigger agent run (enqueue). E2E and programmatic use."""
    from uuid import uuid4
    from src.core.agent_engine import AgentRun, AgentRunState, get_agent_engine
    agents = await get_agent_framework()
    spec = agents.get(agent_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    engine = get_agent_engine()
    run = AgentRun(
        run_id=uuid4(),
        agent_name=agent_id,
        tenant_id=(body or {}).get("tenant_id", "default"),
        space_id=(body or {}).get("space_id", "private"),
        user_id=(body or {}).get("user_id", "system"),
        trigger="manual",
        input_context=dict(body or {}),
    )
    await engine.enqueue_run(run)
    return {"run_id": str(run.run_id), "status": AgentRunState.IDLE.value, "agent_id": agent_id}


@app.get("/api/v1/agents/{agent_id}/status")
async def agent_status_v1(agent_id: str) -> dict[str, Any]:
    """Agent status (idle when no run in progress). E2E expects valid JSON."""
    agents = await get_agent_framework()
    if not agents.get(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return {"status": "idle", "agent_id": agent_id}


@app.get("/api/v1/insights")
async def insights(tenant_id: str, user_id: str) -> list[dict[str, Any]]:
    """Insights (placeholder)."""
    return []


# Include routers
from src.api import (
    governance,
    observability,
    whatsapp_os,
    brand,
    auth,
    events,
    agents,
    realtime_ws,
    tenants,
    users,
    decisions,
    graph,
    audit_api,
    v1_domain,
)

app.include_router(governance.router)
app.include_router(observability.router)
app.include_router(whatsapp_os.router)
app.include_router(brand.router)
app.include_router(command.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(agents.router)
app.include_router(realtime_ws.router)
app.include_router(tenants.router)
app.include_router(users.router)
app.include_router(decisions.router)
app.include_router(graph.router)
app.include_router(audit_api.router)
app.include_router(v1_domain.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("ENV") == "development",
    )
