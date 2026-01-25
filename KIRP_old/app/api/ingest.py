"""
KIRP Ingest API - Unified Production Version
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.services.pipeline import ingest_text
from app.core.persistence import PersistenceManager
from app.api.auth import get_current_user

router = APIRouter(prefix="/ingest", tags=["Ingest"])


class IngestRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}


@router.post("", response_model=Dict[str, Any])
async def ingest_text_endpoint(
    data: IngestRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Production ingestion endpoint:
    - Ingests text into pipeline (RAG / vector store / etc.)
    - Attaches user_id into metadata
    - Persists an 'ingest' event for observability / analytics
    """
    try:
        result = await ingest_text(
            text=data.text,
            source="api",
            metadata={**data.metadata, "user_id": current_user["username"]},
        )

        # Persistence hook — ingest event
        await PersistenceManager.save_event(
            "ingest",
            {
                "source": "api",
                "memory_type": result.get("memory_type"),
                "text_length": len(data.text),
                "user_id": current_user["username"],
            },
        )

        return {
            "success": True,
            "chunks_added": result.get("chunks_added", 0),
            "memory_type": result.get("memory_type"),
        }

    except Exception as e:
        # אפשר להוסיף כאן גם mark_error אם יש לך observability layer
        raise HTTPException(status_code=500, detail=str(e))
