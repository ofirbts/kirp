from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api import ingest, query, health, debug, ingest_batch
from app.api.intelligence.summary import router as intelligence_router
from app.api.intelligence.decay import router as decay_router
from app.api.tasks import router as tasks_router
from app.api.export import router as export_router
from app.rag.vector_store import load_vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🟢 Loading vector store...")
    load_vector_store()
    yield
    print("🔴 Shutting down application")


app = FastAPI(
    title="KIRP AI Platform",
    lifespan=lifespan
)

# Core APIs
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(ingest_batch.router, prefix="/ingest", tags=["Ingest"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(debug.router, prefix="/debug", tags=["Debug"])

# Intelligence
app.include_router(intelligence_router)
app.include_router(decay_router)

# Tasks & Export
app.include_router(tasks_router)
app.include_router(export_router)
