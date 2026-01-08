from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from fastapi.responses import FileResponse 
from fastapi.staticfiles import StaticFiles 
import os

from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.ingest_batch import router as ingest_batch_router
from app.api.query import router as query_router
from app.api.debug import router as debug_router
from app.api.agent import router as agent_router
from app.api.status import router as status_router



print("✅ Core routers loaded")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🔥 Load vector store ב-startup
    print("🧠 Loading vector store...")
    try:
        from app.rag.vector_store import load_vector_store, debug_info
        load_vector_store()
        info = debug_info()
        print(f"✅ Vector store ready: {info}")
    except Exception as e:
        print(f"⚠️ Vector store load: {e}")
    
    yield
    
    print("🔴 KIRP shutdown")



app = FastAPI(title="KIRP AI Platform", lifespan=lifespan)


# routers
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])
app.include_router(ingest_batch_router, prefix="/ingest", tags=["Ingest"])
app.include_router(query_router, prefix="/query", tags=["Query"])
app.include_router(debug_router, prefix="/debug", tags=["Debug"])
app.include_router(agent_router, prefix="/agent", tags=["Agent"])
app.include_router(status_router, prefix="/status", tags=["Status"])



print("🚀 KIRP API fully ready!")


async def confirm_agent(request: dict):
    trace_id = request.get("trace_id")
    confirm = request.get("confirm", True)
    
    if not trace_id:
        return {"error": "trace_id required"}
    
    # קיים logic ליצירת Notion tasks
    from app.services.notion_service import create_notion_tasks
    result = create_notion_tasks(trace_id)
    
    return {
        "status": "executed",
        "action": "create_notion_tasks", 
        "trace_id": trace_id,
        "notion_pages": result.get("notion_pages", 0)
    }

# TASKS & INTELLIGENCE ENDPOINTS - ישירות ב-main
# 🔥 TASKS & INTELLIGENCE - פשוט ותקין
from fastapi import APIRouter, Query
tasks_router = APIRouter(tags=["tasks"], prefix="/tasks")
intelligence_router = APIRouter(tags=["intelligence"], prefix="/intelligence")

@tasks_router.get("/")
async def get_tasks(query: str = Query(None)):
    return {
        "tasks": [
            {"id": 1, "title": "בדוק KIRP Dashboard ✅", "status": "done"},
            {"id": 2, "title": "הוסף זיכרון חדש", "status": "open", "priority": "high"}
        ],
        "summary": "2/5 משימות הושלמו"
    }

@intelligence_router.post("/weekly-summary")
async def weekly_summary():
    return {
        "week": "שבוע 1/2026", 
        "memories": 27,
        "recommendations": ["הוסף זיכרונות יומיים", "בדוק WhatsApp"]
    }

app.include_router(tasks_router)
app.include_router(intelligence_router)
print("✅ Tasks & Intelligence routers loaded")