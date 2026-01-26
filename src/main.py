"""
KIRP Enterprise — FastAPI main app.

North Star: Controlled Intelligence Layer · Event-Sourced · Multi-Tenant · Zero Leakage.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

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
    global _schema_engine
    if _schema_engine is None:
        from src.core.schema_engine import SchemaEngine
        _schema_engine = SchemaEngine(os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp"))
        await _schema_engine.connect()
    return _schema_engine


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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    """Dashboard stats."""
    return {
        "knowledge_items": 0,
        "active_jobs": 0,
        "new_insights": 0,
        "agents": 7,
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
    """List registered agents."""
    agents = await get_agent_framework()
    return [
        {
            "name": s.name,
            "type": s.type,
            "triggers": s.triggers,
            "description": s.description,
        }
        for s in agents.list_all()
    ]


@app.get("/api/v1/insights")
async def insights(tenant_id: str, user_id: str) -> list[dict[str, Any]]:
    """Insights (placeholder)."""
    return []


# Include routers
from src.api import governance, observability, whatsapp_os, brand, auth

app.include_router(governance.router)
app.include_router(observability.router)
app.include_router(whatsapp_os.router)
app.include_router(brand.router)
app.include_router(command.router)
app.include_router(auth.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("ENV") == "development",
    )
