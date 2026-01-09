from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, Query, Request
from contextlib import asynccontextmanager

# Imports של ה-Routers הקיימים
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.ingest_batch import router as ingest_batch_router
from app.api.query import router as query_router
from app.api.query_stream import router as query_stream_router
from app.api.debug import router as debug_router
from app.api.agent import router as agent_router
from app.api.status import router as status_router
from app.api.self_improving import router as self_improving_router
from app.ui.ui import router as ui_router
from app.api.agent_query import router as agent_query_router
from app.api.debug_memory import router as debug_memory_router
from app.api.webhooks_whatsapp import router as whatsapp_router

# --- NEW: Imports של הרכיבים החדשים ---
from app.api.observability import router as observability_router 
from app.api.policy import router as policy_router 
from app.agent.multi_agent import MultiAgentOrchestrator 
from app.agent.negotiation import NegotiationEngine 
from app.agent.tool_agent import ToolAgent

# Core components
from app.rag.vector_store import load_vector_store, debug_info
from app.core.persistence import PersistenceManager
from app.agent.agent import agent
from app.core.state_snapshot import save_snapshot, load_snapshot
from app.core.tenant import TenantContext

# אתחול מופעי הסוכנים
multi_agent = MultiAgentOrchestrator()
negotiation = NegotiationEngine()
tool_agent = ToolAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🧠 Loading vector store...")
    try:
        load_vector_store()
        print("✅ Vector store ready:", debug_info())
    except Exception as e:
        print("⚠️ Vector store load failed:", e)

    try:
        snapshot = load_snapshot()
        if snapshot:
            agent.load_state(snapshot)
            print("🔄 Agent state restored from snapshot")
    except Exception as e:
        print("⚠️ Failed to load snapshot:", e)

    try:
        state = PersistenceManager.load_agent_state()
        if state:
            agent.load_state(state)
            print("✅ Agent state loaded from persistence")
    except Exception as e:
        print("⚠️ Failed to load agent state:", e)

    yield

    # Shutdown logic
    try:
        state_data = agent.dump_state()
        PersistenceManager.save_agent_state(state_data)
        save_snapshot(state_data)
        print("💾 Agent state persisted on shutdown")
    except Exception as e:
        print("⚠️ Failed to save state on shutdown:", e)


app = FastAPI(
    title="KIRP AI Platform",
    lifespan=lifespan,
)

# --- 🚀 הוספת ה-MIDDLEWARE הגלובלי כאן ---
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    # שליפת ה-Tenant מה-Header
    tenant = request.headers.get("X-Tenant", "default")
    # הגדרת ה-Context לפני המשך הטיפול בבקשה
    TenantContext.set(tenant)
    
    response = await call_next(request)
    return response

# --- Register Routers ---

app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(status_router, prefix="/status", tags=["Status"])
app.include_router(debug_router, prefix="/debug", tags=["Debug"])
app.include_router(debug_memory_router, tags=["Debug"])
app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])
app.include_router(ingest_batch_router, prefix="/ingest", tags=["Ingest"])
app.include_router(query_router, prefix="/query", tags=["Query"])
app.include_router(query_stream_router, prefix="/query", tags=["Query Stream"])
app.include_router(agent_router, prefix="/agent", tags=["Agent"])
app.include_router(agent_query_router, prefix="/agent/query", tags=["Agent Query"])
app.include_router(self_improving_router, prefix="/agent", tags=["Agent"])
app.include_router(observability_router, prefix="/observability", tags=["Observability"])
app.include_router(policy_router, prefix="/policy", tags=["Policy"])
app.include_router(ui_router, prefix="/ui", tags=["UI"])
governance_router = APIRouter(prefix="/governance", tags=["Governance"])
app.include_router(governance_router)
app.include_router(whatsapp_router)


# Custom Business Logic Routers
tasks_router = APIRouter(tags=["tasks"], prefix="/tasks")
intelligence_router = APIRouter(tags=["intelligence"], prefix="/intelligence")

@tasks_router.get("/")
async def get_tasks(query: str = Query(None)):
    return {
        "tasks": [
            {"id": 1, "title": "בדוק KIRP Dashboard ✅", "status": "done"},
            {"id": 2, "title": "הוסף זיכרון חדש", "status": "open", "priority": "high"},
        ],
        "summary": "2/5 משימות הושלמו",
    }

@intelligence_router.post("/weekly-summary")
async def weekly_summary():
    return {
        "week": "שבוע 1/2026",
        "memories": 27,
        "recommendations": ["הוסף זיכרונות יומיים", "בדוק WhatsApp"],
    }

app.include_router(tasks_router)
app.include_router(intelligence_router)

print("🚀 KIRP API fully ready with Multi-Agent and Tenant Middleware!")