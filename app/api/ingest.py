from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import Any, Dict, Any

router = APIRouter(tags=["Ingest"])

class IngestRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

@router.post("/")
async def ingest_text(data: IngestRequest):
    return {"status": "ingested", "text": data.text[:50] + "..."}
