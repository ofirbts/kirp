from fastapi import FastAPI
from app.api import ingest, query, health, debug

app = FastAPI(title="KIRP AI Platform")

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(debug.router, prefix="/debug", tags=["Debug"])
