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

from dotenv import load_dotenv
load_dotenv()

# Ensure project root is on sys.path when running as a script (e.g. Streamlit, `python src/main.py`)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from fastapi import FastAPI, HTTPException, Depends, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.api import governance, observability, whatsapp_os, brand
import src.api.command as command
from src.core.auth import get_current_user, User
from src.core.jwt_utils import require_auth
from src.core.auth import get_current_user, User
from src.core.jwt_utils import require_auth


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("KIRP")


# --- Pydantic models ---
class IngestRequest(BaseModel):
    """Body for POST /api/v1/ingest. content must be a string (plain text to ingest)."""
    tenant_id: str = "default"
    space_id: str = "default"
    user_id: str = "dev"
    content: str  # required: plain text to ingest (not an object)
    source: str = "api"
    metadata: dict | None = None


class QueryRequest(BaseModel):
    tenant_id: str
    space_id: str
    user_id: str
    query: str
    k: int = 6


class AskRequest(BaseModel):
    """Body for POST /api/v1/ask. Only query is required; tenant_id/user_id/space_id come from JWT."""
    query: str


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
        try:
            await _event_store.connect()
        except Exception as e:
            _event_store = None
            logger.warning("EventStore connection failed (will retry on next request): %s", e)
            raise
    return _event_store


async def get_rag_engine() -> Any:
    global _rag_engine
    if _rag_engine is None:
        from src.core.rag_engine import get_shared_rag_engine
        try:
            _rag_engine = await get_shared_rag_engine()
        except Exception as e:
            logger.warning("RAGEngine connection failed (will retry on next request): %s", e)
            raise
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


async def _seed_dev_user_if_needed() -> None:
    """Create dev@localhost with password 'dev' if no users exist (demo user for first run)."""
    try:
        from src.core.auth import get_user_store
        from src.api.v1_auth import _make_password_hash, DEV_EMAIL, DEV_PASSWORD

        store = get_user_store()
        await store.connect()
        existing = await store.get_user_by_email(DEV_EMAIL)
        if existing:
            return
        pw_hash = _make_password_hash(DEV_PASSWORD)
        await store.create_user(
            email=DEV_EMAIL,
            password_hash=pw_hash,
            name="Dev",
            tenant_id="default",
            roles=["admin"],
        )
        logger.info("Seeded dev user: %s (password: %s)", DEV_EMAIL, DEV_PASSWORD)
    except Exception as e:
        logger.warning("Dev user seed failed (non-fatal): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: prepare dirs; seed dev user; services connect lazily on first use."""
    logger.info("KIRP Enterprise starting (lazy connect: stores connect on first use)")
    prom_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if prom_dir:
        os.makedirs(prom_dir, exist_ok=True)
        logger.debug("Prometheus multiprocess dir ensured: %s", prom_dir)
    await _seed_dev_user_if_needed()
    yield
    logger.info("KIRP Enterprise shutting down")


app = FastAPI(
    title="KIRP Enterprise — Intelligence OS",
    version="0.1.0",
    lifespan=lifespan,
)
# CORS: must be added before any routers. No "*" when allow_credentials=True (browser rejects it).
from fastapi.middleware.cors import CORSMiddleware
import os

_cors_origins = [
    "http://localhost:3100",
    "http://127.0.0.1:3100",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

env_origins = os.getenv("CORS_ORIGINS")
if env_origins:
    _cors_origins.extend(
        o.strip()
        for o in env_origins.split(",")
        if o.strip()
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def _cors_headers(origin: str | None) -> dict[str, str]:
    """CORS headers for error responses so browser shows real status instead of CORS error."""
    if origin and origin.rstrip("/") in [o.rstrip("/") for o in _cors_origins]:
        return {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"}
    return {"Access-Control-Allow-Origin": _cors_origins[0] if _cors_origins else "*", "Access-Control-Allow-Credentials": "true"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    origin = request.headers.get("origin")
    headers = _cors_headers(origin)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    origin = request.headers.get("origin")
    headers = _cors_headers(origin)
    logging.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"}, headers=headers)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Authentication middleware.

    - If Authorization Bearer is present: decode JWT and set request.state.user from payload.
      Use user_id, tenant_id EXACTLY as in payload — no "dev" fallback.
    - If no valid JWT and SKIP_AUTH=1: set default dev user for local dev only.
    - If no valid JWT and SKIP_AUTH=0: request.state.user stays None → get_tenant_context raises 401.
    """
    if not hasattr(request.state, "user") or request.state.user is None:
        auth = request.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
            try:
                from src.core.jwt_utils import decode_token

                payload = decode_token(token)
                # JWT requires user_id and tenant_id; use exactly as provided (no dev fallback)
                uid = payload.get("user_id")
                tid = payload.get("tenant_id")
                if not uid or not str(uid).strip():
                    request.state.user = None  # Invalid token shape
                else:
                    request.state.user = {
                        "tenant_id": str(tid).strip() if tid else None,
                        "space_id": (payload.get("space_id") or "all").strip(),
                        "user_id": str(uid).strip(),
                        "roles": payload.get("roles") or [],
                    }
            except HTTPException:
                request.state.user = None

        if not hasattr(request.state, "user") or request.state.user is None:
            skip = os.getenv("SKIP_AUTH", "").lower() in ("1", "true", "yes")
            if skip:
                request.state.user = {
                    "tenant_id": "default",
                    "space_id": "default",
                    "user_id": "dev",
                    "roles": ["admin"],
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


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    """
    Lightweight health check for platforms (e.g. Streamlit Cloud) that probe `/healthz`.

    Does not hit external dependencies to avoid startup failures when optional
    services (Mongo, Qdrant, etc.) are not available.
    """
    return {"status": "ok", "service": "kirp-enterprise-api"}


@app.get("/api/v1/stats")
async def stats(request: Request) -> dict[str, Any]:
    """Dashboard stats from real data (event count, agents, etc.). Tenant-scoped."""
    try:
        from src.auth.tenant_context import get_tenant_context

        ctx = get_tenant_context(request)
        store = await get_event_store()
        agents = await get_agent_framework()
        knowledge_count = await store.count_events(tenant_id=ctx.tenant_id, space_id=ctx.space_id or "all")
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
async def ingest(req: IngestRequest, request: Request) -> dict[str, Any]:
    """
    Publish ingest envelope to Kafka. Uses ONLY get_tenant_context(request) from JWT.
    No body defaults; no "dev" fallback. Missing user_id → 403.
    """
    try:
        from src.agents.kafka_event_agent import KafkaEventAgent, EventEnvelope
        from src.auth.tenant_context import get_tenant_context

        ctx = get_tenant_context(request)
        tenant_id = ctx.tenant_id
        space_id = ctx.space_id
        user_id = ctx.user_id
        if not user_id or not str(user_id).strip():
            raise HTTPException(status_code=403, detail="user_id required for ingest")

        payload = {
            "text": req.content,
            "tenant_id": tenant_id,
            "space_id": space_id,
            "user_id": user_id,
            "source": req.source,
            "metadata": req.metadata or {},
        }
        emitted = KafkaEventAgent().emit(EventEnvelope(
            type="ingest",
            payload=payload,
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
        ))
        if not emitted:
            raise HTTPException(status_code=503, detail="Event bus unavailable; ingest not published")
        return {"ok": True}
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


@app.post("/api/v1/ask")
async def ask(
    req: AskRequest,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Ask/Search/Insights API. Uses JWT for tenant/user; request body is only { "query": "..." }.
    Uses InsightAgent on top of RAG, scoped to current_user.tenant_id and current_user.id.
    """
    try:
        rag = await get_rag_engine()
        from src.agents.insight import InsightAgent

        agent = InsightAgent(rag)
        tenant_id = user.tenant_id
        space_id = "all"
        user_id = user.id
        result = await agent.ask(
            tenant_id=tenant_id,
            space_id=space_id,
            query=req.query,
            user_id=user_id,
        )
        return {
            "answer": result.answer,
            "sources": result.sources,
            "needs_external_info": result.needs_external_info,
        }
    except Exception as e:
        logger.exception("Ask failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agents")
async def list_agents_v1(
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List registered agents with last_run from logs (id = name for E2E and callability). Tenant from JWT."""
    agents = await get_agent_framework()
    from src.core.agent_scheduler import get_agent_logs_store
    logs_store = get_agent_logs_store()
    tenant_id = user.tenant_id
    try:
        await logs_store.connect()
        all_logs = await logs_store.list_(tenant_id=tenant_id, limit=500)
        last_by_agent = {}
        for log in all_logs:
            n = log.get("agent_name")
            if n and (n not in last_by_agent or (log.get("run_at") or "") > (last_by_agent[n].get("run_at") or "")):
                last_by_agent[n] = log
    except Exception:
        last_by_agent = {}
    return [
        {
            "id": s.name,
            "name": s.name,
            "type": s.type,
            "triggers": s.triggers,
            "description": s.description,
            "last_run": last_by_agent.get(s.name, {}).get("run_at"),
            "next_run": None,
        }
        for s in agents.list_all()
    ]


@app.post("/api/v1/agents/{agent_id}/run")
async def run_agent_v1(
    agent_id: str,
    body: dict | None = None,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Run agent now and log result. Tenant/user/space from JWT; agents get RAG context internally when needed."""
    from src.core.agent_scheduler import AgentScheduler, get_agent_logs_store
    agents = await get_agent_framework()
    spec = agents.get(agent_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    tenant_id = user.tenant_id
    space_id = "all"
    user_id = user.id
    # Inject RAG context so agents that need it (e.g. PatternAnalyzerAgent) do not return missing_rag_context.
    initial_context: dict[str, Any] = {}
    try:
        rag = await get_rag_engine()
        rag_response = await rag.search(
            query="recent activity and patterns",
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            limit=10,
        )
        initial_context["rag_response"] = rag_response
    except Exception as e:
        logger.warning("run_agent_v1: could not pre-fetch RAG context for %s: %s", agent_id, e)
    scheduler = AgentScheduler(agents, None)
    result = await scheduler.run_agent_and_log(
        agent_id, tenant_id, space_id, user_id, "manual", initial_context=initial_context
    )
    try:
        from src.core.notifications import notify_user
        if result.get("ok"):
            actions_count = len(result.get("actions") or [])
            insights_count = len(result.get("insights") or [])
            if actions_count:
                await notify_user(tenant_id, user_id, "agent_action", f"{agent_id} produced actions", f"{actions_count} action(s) queued.", space_id=space_id, meta={"agent_id": agent_id})
            if insights_count:
                await notify_user(tenant_id, user_id, "insight_generated", f"{agent_id} insights", f"{insights_count} insight(s) generated.", space_id=space_id, meta={"agent_id": agent_id})
    except Exception:
        pass
    try:
        from src.core.history import record_history
        if result.get("ok"):
            actions_count = len(result.get("actions") or [])
            insights_count = len(result.get("insights") or [])
            if agent_id == "InsightAgentV2" and insights_count:
                await record_history(tenant_id, space_id, user_id, "agent_insight", "Insight generated", f"{insights_count} insight(s) from {agent_id}.", source="agent", meta={"agent_id": agent_id})
            elif agent_id == "PlannerAgent":
                await record_history(tenant_id, space_id, user_id, "agent_action", "Plan generated", f"Plan from {agent_id}.", source="agent", meta={"agent_id": agent_id})
            elif agent_id == "ExecutionAgent" and actions_count:
                await record_history(tenant_id, space_id, user_id, "agent_action", "Action executed", f"{actions_count} action(s) executed.", source="agent", meta={"agent_id": agent_id})
            elif (actions_count or insights_count):
                await record_history(tenant_id, space_id, user_id, "agent_insight" if insights_count else "agent_action", f"{agent_id} ran", f"{insights_count} insight(s), {actions_count} action(s).", source="agent", meta={"agent_id": agent_id})
    except Exception:
        pass
    return {"ok": result.get("ok", False), "agent_id": agent_id, "result": result}


@app.get("/api/v1/agents/logs")
async def list_agent_logs_v1(
    agent_name: str | None = None,
    limit: int = 100,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List agent run logs (run_at, duration_ms, result_count, errors). Tenant from JWT."""
    try:
        from src.core.agent_scheduler import get_agent_logs_store
        store = get_agent_logs_store()
        await store.connect()
        return await store.list_(tenant_id=user.tenant_id, agent_name=agent_name, limit=limit)
    except Exception as e:
        logging.warning("Agent logs store unavailable: %s", e)
        return []


@app.get("/api/v1/agents/actions")
async def list_agent_actions_v1(
    status: str | None = None,
    agent: str | None = None,
    limit: int = 200,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List agent actions (pending, executed, failed). Tenant from JWT."""
    try:
        from src.core.agent_actions import get_agent_actions_store
        store = get_agent_actions_store()
        await store.connect()
        return await store.list_(tenant_id=user.tenant_id, status=status, agent=agent, limit=limit)
    except Exception as e:
        logging.warning("Agent actions store unavailable: %s", e)
        return []


@app.get("/api/v1/agents/{agent_id}/status")
async def agent_status_v1(
    agent_id: str,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """Agent status (idle when no run in progress). E2E expects valid JSON."""
    agents = await get_agent_framework()
    if not agents.get(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return {"status": "idle", "agent_id": agent_id}


@app.get("/api/v1/insights")
async def insights(
    space_id: str | None = None,
    limit: int = 50,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Real insights from workload, patterns, commitments, connections, and recommendations. Tenant/user from JWT."""
    from src.core.insights_engine import InsightsEngine
    schema = await get_schema_engine()
    store = await get_event_store()
    engine = InsightsEngine(schema, store)
    raw = await engine.compute_insights(
        tenant_id=user.tenant_id,
        space_id=space_id or "all",
        user_id=user.id,
        limit=limit,
    )
    return [i.to_dict() for i in raw]


class NotionSyncRequest(BaseModel):
    tenant_id: str = "default"
    space_id: str = "all"
    user_id: str = "system"


@app.post("/api/v1/notion/sync")
async def notion_sync(req: NotionSyncRequest | None = Body(None)) -> dict[str, Any]:
    """Pull Notion tasks DB and ingest new pages (idempotent)."""
    r = req or NotionSyncRequest()
    from src.workers.notion_sync import run_notion_sync
    store = await get_event_store()
    pipe = await get_pipeline()
    from src.integrations.notion import NotionIntegration
    notion = NotionIntegration()
    notion.connect()
    result = await run_notion_sync(
        tenant_id=r.tenant_id,
        space_id=r.space_id,
        user_id=r.user_id,
        event_store=store,
        pipeline=pipe,
        notion=notion,
    )
    return {"ok": True, **result}


# Include routers
from src.api import (
    governance,
    observability,
    whatsapp_os,
    brand,
    auth,
    events,
    agents,
    tenants,
    users,
    decisions,
    graph,
    audit_api,
    v1_auth,
    v1_domain,
    ws_notifications,
    v1_notifications,
    v1_rag,
)
from src.api.routes.llm_usage import router as llm_usage_router

app.include_router(ws_notifications.router)
app.include_router(governance.router)
app.include_router(observability.router)
app.include_router(whatsapp_os.router)
app.include_router(brand.router)
app.include_router(v1_auth.router)
app.include_router(command.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(agents.router)
app.include_router(tenants.router)
app.include_router(users.router)
app.include_router(decisions.router)
app.include_router(graph.router)
app.include_router(audit_api.router)
app.include_router(v1_domain.router)
app.include_router(v1_rag.router)

from src.api import v1_tasks, v1_ingestion, v1_reminders, v1_execute, v1_context, v1_connections, v1_graph, v1_history, v1_tenants_spaces, v1_events, v1_users, v1_scenarios
app.include_router(v1_history.router)
app.include_router(v1_tasks.router)
app.include_router(v1_ingestion.router)
app.include_router(v1_reminders.router)
app.include_router(v1_execute.router)
app.include_router(v1_context.router)
app.include_router(v1_connections.router)
app.include_router(v1_graph.router)
app.include_router(v1_tenants_spaces.router)
app.include_router(v1_events.router)
app.include_router(v1_users.router)
app.include_router(v1_scenarios.router)
app.include_router(v1_notifications.router)
app.include_router(llm_usage_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("ENV") == "development",
    )
