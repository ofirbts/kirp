from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging

from app.api import ingest, query, health, debug, ingest_batch
from app.api.intelligence.summary import router as intelligence_router
from app.api.intelligence.decay import router as decay_router
from app.api.tasks import router as tasks_router
from app.api.export import router as export_router
from app.rag.vector_store import load_vector_store
from app.agent.loop import agent_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🟢 Loading vector store...")
    load_vector_store()  # ללא await - זה sync!
    
    print("🤖 Starting agent loop...")
    app.state.agent_task = asyncio.create_task(agent_loop())
    
    yield
    
    print("🔴 Shutting down...")
    app.state.agent_task.cancel()
    try:
        await app.state.agent_task
    except asyncio.CancelledError:
        pass



app = FastAPI(
    title="KIRP AI Platform",
    lifespan=lifespan
)

# Routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(ingest_batch.router, prefix="/ingest", tags=["Ingest"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(debug.router, prefix="/debug", tags=["Debug"])
app.include_router(intelligence_router)
app.include_router(decay_router)
app.include_router(tasks_router)
app.include_router(export_router)
