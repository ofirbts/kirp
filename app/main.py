from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, Query
from contextlib import asynccontextmanager

from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.ingest_batch import router as ingest_batch_router
from app.api.query import router as query_router
from app.api.query_stream import router as query_stream_router   # ← חשוב
from app.api.debug import router as debug_router
from app.api.agent import router as agent_router
from app.api.status import router as status_router
from app.api.self_improving import router as self_improving_router

from app.rag.vector_store import load_vector_store, debug_info


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🧠 Loading vector store...")
    try:
        load_vector_store()
        print("✅ Vector store ready:", debug_info())
    except Exception as e:
        print("⚠️ Vector store load failed:", e)
    yield
    print("🔴 KIRP shutdown")


app = FastAPI(title="KIRP AI Platform", lifespan=lifespan)

# Core routers
app.include_router(query_router, prefix="/query", tags=["Query"])
app.include_router(query_stream_router, prefix="/query", tags=["Query Stream"])  # ← מוסיפים
app.include_router(self_improving_router, prefix="/agent", tags=["Agent"])
app.include_router(agent_router, prefix="/agent", tags=["Agent"])
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])
app.include_router(ingest_batch_router, prefix="/ingest", tags=["Ingest"])
app.include_router(debug_router, prefix="/debug", tags=["Debug"])
app.include_router(status_router, prefix="/status", tags=["Status"])

# Tasks & Intelligence
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

print("🚀 KIRP API fully ready!")
