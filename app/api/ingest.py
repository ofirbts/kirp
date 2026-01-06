from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from app.services.pipeline import ingest_text

router = APIRouter(tags=["Ingest"])

class IngestRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

@router.post("/")
def ingest_text_endpoint(data: IngestRequest):  # ← def, לא async def!
    """✅ Working pipeline - memory_type in sources!"""
    result = ingest_text(data.text, "api", data.metadata)  # ← no await!
    return {
        "status": result["status"],
        "chunks_added": result["chunks_added"],
        "memory_type": result["memory_type"]
    }
