from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

# Core routers - הסר tasks זמנית
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.ingest_batch import router as ingest_batch_router
from app.api.query import router as query_router
from app.api.debug import router as debug_router
from app.api.agent import router as agent_router

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

# חיבור routers - ללא tasks
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])
app.include_router(ingest_batch_router, prefix="/ingest", tags=["Ingest"])
app.include_router(query_router, prefix="/query", tags=["Query"])
app.include_router(debug_router, prefix="/debug", tags=["Debug"])
app.include_router(agent_router, prefix="/agent", tags=["Agent"])

print("🚀 KIRP API fully ready!")
