from fastapi import FastAPI
from app.api import ingest, query, health, debug
from app.rag.vector_store import load_vector_store
from app.api import ingest_batch

app = FastAPI(title="KIRP AI Platform")


@app.on_event("startup")
def startup_event():
    """
    Load vector store if exists.
    If not – system still runs (ingest will create it).
    """
    load_vector_store()


app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(debug.router, prefix="/debug", tags=["Debug"])
app.include_router(ingest_batch.router, prefix="/ingest", tags=["Ingest"])

