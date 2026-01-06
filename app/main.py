from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

# Core routers - ישיר
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.ingest_batch import router as ingest_batch_router
from app.api.query import router as query_router
from app.api.debug import router as debug_router
from app.api.tasks import router as tasks_router

print("✅ Core routers loaded")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("�� KIRP startup complete")
    yield
    print("🔴 KIRP shutdown")

app = FastAPI(title="KIRP AI Platform", lifespan=lifespan)

# חיבור routers
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])
app.include_router(ingest_batch_router, prefix="/ingest", tags=["Ingest"])
app.include_router(query_router, prefix="/query", tags=["Query"])
app.include_router(debug_router, prefix="/debug", tags=["Debug"])
app.include_router(tasks_router)

print("🚀 KIRP API fully ready!")
