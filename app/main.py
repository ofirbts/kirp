import logging
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager

# ייבוא הראוטרים
from app.api.health import router as health_router
from app.api.query import router as query_router
from app.api.webhooks_whatsapp import router as whatsapp_router

# ייבוא ה-Agent וה-Store לאתחול
from app.rag.qdrant_store import init_collection

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # אתחול המערכת בעליית השרת
    logger.info("Initializing KIRP OS Services...")
    try:
        init_collection() # מוודא שהקולקציה ב-Qdrant קיימת
        logger.info("Qdrant store ready.")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {e}")
    
    yield
    logger.info("Shutting down KIRP OS...")

app = FastAPI(
    title="KIRP AI Platform",
    lifespan=lifespan
)

# רישום הראוטרים
app.include_router(health_router, prefix="/health")
app.include_router(query_router, prefix="/api/v1") # נתיב לשילוב עם ה-UI/API
app.include_router(whatsapp_router) # ה-prefix כבר מוגדר בתוך הראוטר כ-/webhooks/whatsapp

@app.get("/")
async def root():
    return {
        "app": "KIRP OS",
        "version": "2.1.0",
        "status": "operational",
        "engine": "CoreAgent v1"
    }