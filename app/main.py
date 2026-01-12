import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.query import router as query_router
from app.api.health import router as health_router
from app.rag.vector_store import load_vector_store

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_vector_store()
    yield

app = FastAPI(
    title="KIRP AI Platform",
    lifespan=lifespan
)

app.include_router(health_router, prefix="/health")
app.include_router(query_router, prefix="/query")

@app.get("/")
async def root():
    return {
        "app": "KIRP",
        "status": "running"
    }
